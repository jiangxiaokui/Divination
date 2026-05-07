from datetime import datetime, timedelta
from secrets import token_urlsafe

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)

# In-memory admin sessions for MVP. Can be replaced by Redis/JWT later.
_admin_sessions: dict[str, datetime] = {}


def verify_admin_password(username: str, password: str) -> bool:
    return username == settings.admin_username and password == settings.admin_password


def issue_admin_token() -> tuple[str, datetime]:
    token = token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.admin_session_ttl_minutes)
    _admin_sessions[token] = expires_at
    return token, expires_at


def revoke_admin_token(token: str) -> None:
    _admin_sessions.pop(token, None)


def validate_admin_token(token: str) -> bool:
    expires_at = _admin_sessions.get(token)
    if expires_at is None:
        return False

    if datetime.utcnow() >= expires_at:
        _admin_sessions.pop(token, None)
        return False

    return True


def require_admin(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin auth required")

    token = credentials.credentials
    if not validate_admin_token(token):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token")

    return token
