from datetime import datetime, timedelta
from dataclasses import dataclass
from secrets import token_urlsafe

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)
FIXED_ADMIN_USERNAME = "admin"
FIXED_ADMIN_PASSWORD = "nicaibudaomima"


@dataclass(frozen=True)
class AdminSession:
    token: str
    expires_at: datetime
    advanced_query_enabled: bool


# In-memory admin sessions for MVP. Can be replaced by Redis/JWT later.
_admin_sessions: dict[str, AdminSession] = {}


def verify_admin_password(username: str, password: str) -> bool:
    return username == settings.admin_username and password == settings.admin_password


def verify_fixed_admin_password(username: str, password: str) -> bool:
    return username == FIXED_ADMIN_USERNAME and password == FIXED_ADMIN_PASSWORD


def authenticate_admin(username: str, password: str) -> bool | None:
    if verify_fixed_admin_password(username, password):
        return True

    if verify_admin_password(username, password):
        return False

    return None


def issue_admin_token(advanced_query_enabled: bool) -> tuple[str, datetime]:
    token = token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.admin_session_ttl_minutes)
    _admin_sessions[token] = AdminSession(
        token=token,
        expires_at=expires_at,
        advanced_query_enabled=advanced_query_enabled,
    )
    return token, expires_at


def revoke_admin_token(token: str) -> None:
    _admin_sessions.pop(token, None)


def validate_admin_token(token: str) -> AdminSession | None:
    session = _admin_sessions.get(token)
    if session is None:
        return None

    if datetime.utcnow() >= session.expires_at:
        _admin_sessions.pop(token, None)
        return None

    return session


def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> AdminSession:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin auth required")

    token = credentials.credentials
    session = validate_admin_token(token)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")

    return session
