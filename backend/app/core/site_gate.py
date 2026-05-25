import hashlib
import hmac
import time
from secrets import compare_digest

from fastapi import Request

from app.core.config import get_settings

settings = get_settings()
_COOKIE_NAME = "site_gate"


def _sign(payload: str) -> str:
    secret = settings.site_gate_cookie_secret.encode("utf-8")
    return hmac.new(secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def issue_site_gate_token() -> str:
    expires_at = int(time.time()) + settings.site_gate_ttl_seconds
    payload = str(expires_at)
    return f"{payload}.{_sign(payload)}"


def validate_site_gate_token(token: str | None) -> bool:
    if not token or "." not in token:
        return False

    payload, signature = token.rsplit(".", 1)
    if not payload.isdigit():
        return False

    expected = _sign(payload)
    if not compare_digest(signature, expected):
        return False

    if int(time.time()) >= int(payload):
        return False

    return True


def verify_site_gate_password(password: str) -> bool:
    expected = settings.site_gate_password
    if not expected:
        return False
    return compare_digest(password.encode("utf-8"), expected.encode("utf-8"))


def request_has_site_gate(request: Request) -> bool:
    return validate_site_gate_token(request.cookies.get(_COOKIE_NAME))


def site_gate_cookie_name() -> str:
    return _COOKIE_NAME
