from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)
TOKEN_TTL_DAYS = 14
AES_NONCE_SIZE = 12


@dataclass(frozen=True)
class UserSession:
    token: str
    user_id: int
    username: str
    expires_at: datetime


def hash_password(password: str) -> str:
    key = _password_cipher_key()
    nonce = os.urandom(AES_NONCE_SIZE)
    ciphertext = AESGCM(key).encrypt(nonce, password.encode("utf-8"), None)
    return "aes256_gcm${nonce}${ciphertext}".format(
        nonce=base64.b64encode(nonce).decode("ascii"),
        ciphertext=base64.b64encode(ciphertext).decode("ascii"),
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    decrypted = decrypt_password(encoded_hash)
    return decrypted is not None and hmac.compare_digest(decrypted, password)


def decrypt_password(encoded_hash: str) -> str | None:
    try:
        algorithm, nonce_b64, ciphertext_b64 = encoded_hash.split("$", 2)
    except ValueError:
        return None

    if algorithm != "aes256_gcm":
        return None

    try:
        nonce = base64.b64decode(nonce_b64.encode("ascii"))
        ciphertext = base64.b64decode(ciphertext_b64.encode("ascii"))
        plaintext = AESGCM(_password_cipher_key()).decrypt(nonce, ciphertext, None)
        return plaintext.decode("utf-8")
    except Exception:
        return None


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}".encode("ascii"))


def _token_secret() -> bytes:
    return settings.user_token_secret.encode("utf-8")


def _password_cipher_key() -> bytes:
    return hashlib.sha256(settings.user_password_aes_secret.encode("utf-8")).digest()


def _sign_token(payload_segment: str) -> str:
    digest = hmac.new(_token_secret(), payload_segment.encode("ascii"), hashlib.sha256).digest()
    return _b64url_encode(digest)


def _encode_token(payload: dict) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    payload_segment = _b64url_encode(payload_json.encode("utf-8"))
    signature_segment = _sign_token(payload_segment)
    return f"{payload_segment}.{signature_segment}"


def _decode_token(token: str) -> dict | None:
    try:
        payload_segment, signature_segment = token.split(".", 1)
    except ValueError:
        return None

    expected_signature = _sign_token(payload_segment)
    if not hmac.compare_digest(signature_segment, expected_signature):
        return None

    try:
        payload_raw = _b64url_decode(payload_segment)
        return json.loads(payload_raw.decode("utf-8"))
    except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def issue_user_token(user_id: int, username: str) -> tuple[str, datetime]:
    expires_at = datetime.utcnow() + timedelta(days=TOKEN_TTL_DAYS)
    token = _encode_token(
        {
            "uid": user_id,
            "usr": username,
            "exp": int(expires_at.timestamp()),
        }
    )
    return token, expires_at


def revoke_user_token(token: str) -> None:
    return None


def validate_user_token(token: str) -> UserSession | None:
    payload = _decode_token(token)
    if payload is None:
        return None

    try:
        user_id = int(payload["uid"])
        username = str(payload["usr"])
        expires_at = datetime.utcfromtimestamp(int(payload["exp"]))
    except (KeyError, TypeError, ValueError, OSError):
        return None

    if datetime.utcnow() >= expires_at:
        return None

    return UserSession(
        token=token,
        user_id=user_id,
        username=username,
        expires_at=expires_at,
    )


def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> UserSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user auth required")

    session = validate_user_token(credentials.credentials)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired user token")

    return session


def get_optional_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> UserSession | None:
    if credentials is None or credentials.scheme.lower() != "bearer":
        return None
    return validate_user_token(credentials.credentials)