from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.admin_auth import issue_admin_token, require_admin, revoke_admin_token, verify_admin_password
from app.core.config import get_settings
from app.db.session import get_db
from app.models.divination_record import DivinationRecord
from app.models.divination_session import DivinationSession
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminRecordItem,
    AdminRecordListResponse,
    AdminRuntimeStatusResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest) -> AdminLoginResponse:
    if not verify_admin_password(payload.username, payload.password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token, expires_at = issue_admin_token()
    return AdminLoginResponse(access_token=token, expires_at=expires_at)


@router.post("/logout")
def admin_logout(token: str = Depends(require_admin)) -> dict:
    revoke_admin_token(token)
    return {"ok": True}


@router.get("/runtime", response_model=AdminRuntimeStatusResponse)
def admin_runtime_status(_: str = Depends(require_admin)) -> AdminRuntimeStatusResponse:
    return AdminRuntimeStatusResponse(
        db_persistence_enabled=settings.db_persistence_enabled,
        app_env=settings.app_env,
    )


@router.get("/records", response_model=AdminRecordListResponse)
def admin_records(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: str = Depends(require_admin),
    db: Session | None = Depends(get_db),
) -> AdminRecordListResponse:
    if not settings.db_persistence_enabled or db is None:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    stmt = (
        select(DivinationRecord, DivinationSession)
        .join(DivinationSession, DivinationSession.id == DivinationRecord.session_id)
        .order_by(DivinationRecord.created_at.desc(), DivinationRecord.id.desc())
        .limit(limit)
        .offset(offset)
    )

    rows = db.execute(stmt).all()
    items = [
        AdminRecordItem(
            record_id=record.id,
            session_id=session.id,
            module=record.module,
            question=session.question,
            created_at=record.created_at,
            has_user=session.user_id is not None,
        )
        for record, session in rows
    ]

    return AdminRecordListResponse(total=len(items), items=items)
