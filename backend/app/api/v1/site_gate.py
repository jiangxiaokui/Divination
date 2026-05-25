from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.site_gate import (
    issue_site_gate_token,
    site_gate_cookie_name,
    verify_site_gate_password,
)

router = APIRouter(prefix="/site-gate", tags=["site-gate"])
settings = get_settings()


class SiteGateLoginIn(BaseModel):
    password: str = Field(min_length=1, max_length=256)


@router.post("/login")
def login(payload: SiteGateLoginIn, response: Response) -> dict:
    if not settings.site_gate_enabled:
        return {"ok": True, "gate": "disabled"}

    if not verify_site_gate_password(payload.password):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="invalid password")

    token = issue_site_gate_token()
    response.set_cookie(
        key=site_gate_cookie_name(),
        value=token,
        httponly=True,
        samesite="lax",
        max_age=settings.site_gate_ttl_seconds,
        secure=settings.site_gate_cookie_secure,
        path="/",
    )
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(key=site_gate_cookie_name(), path="/")
    return {"ok": True}
