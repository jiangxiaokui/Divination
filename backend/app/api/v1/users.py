from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.user_auth import (
    UserSession,
    hash_password,
    issue_user_token,
    require_user,
    revoke_user_token,
    verify_password,
)
from app.db.session import get_db
from app.models.divination_record import DivinationRecord
from app.models.divination_session import DivinationSession
from app.models.user import User
from app.schemas.reading import HistoryRecordOut, SessionHistoryOut, UserHistoryOut
from app.schemas.user import UserAuthResponse, UserLogin, UserOut, UserProfileUpdate, UserRegister

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


def _build_user_out(user: User) -> UserOut:
    return UserOut.model_validate(user)


@router.post("/register", response_model=UserAuthResponse)
def register_user(payload: UserRegister, db: Session | None = Depends(get_db)) -> UserAuthResponse:
    if not settings.db_persistence_enabled or db is None:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    existing = db.scalar(select(User).where(User.username == payload.username.strip()))
    if existing is not None:
        raise HTTPException(status_code=409, detail="username already exists")

    user = User(
        username=payload.username.strip(),
        nickname=payload.nickname.strip(),
        password_hash=hash_password(payload.password),
        profile_payload=payload.profile_payload,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token, expires_at = issue_user_token(user.id, user.username)
    return UserAuthResponse(access_token=token, expires_at=expires_at, user=_build_user_out(user))


@router.post("/login", response_model=UserAuthResponse)
def login_user(payload: UserLogin, db: Session | None = Depends(get_db)) -> UserAuthResponse:
    if not settings.db_persistence_enabled or db is None:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    user = db.scalar(select(User).where(User.username == payload.username.strip()))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token, expires_at = issue_user_token(user.id, user.username)
    return UserAuthResponse(access_token=token, expires_at=expires_at, user=_build_user_out(user))


@router.post("/logout")
def logout_user(session: UserSession = Depends(require_user)) -> dict:
    revoke_user_token(session.token)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
def get_me(session: UserSession = Depends(require_user), db: Session | None = Depends(get_db)) -> UserOut:
    if db is None:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return _build_user_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(
    payload: UserProfileUpdate,
    session: UserSession = Depends(require_user),
    db: Session | None = Depends(get_db),
) -> UserOut:
    if db is None:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    user.nickname = payload.nickname.strip()
    user.profile_payload = payload.profile_payload
    db.add(user)
    db.commit()
    db.refresh(user)
    return _build_user_out(user)


@router.get("/me/history", response_model=UserHistoryOut)
def get_my_history(
    session: UserSession = Depends(require_user),
    db: Session | None = Depends(get_db),
) -> UserHistoryOut:
    if db is None:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    session_rows = db.scalars(
        select(DivinationSession)
        .where(DivinationSession.user_id == session.user_id)
        .order_by(DivinationSession.created_at.desc(), DivinationSession.id.desc())
    ).all()

    session_items: list[SessionHistoryOut] = []
    for session_obj in session_rows:
        records = db.scalars(
            select(DivinationRecord)
            .where(DivinationRecord.session_id == session_obj.id)
            .order_by(DivinationRecord.created_at.asc(), DivinationRecord.id.asc())
        ).all()

        session_items.append(
            SessionHistoryOut(
                session_id=session_obj.id,
                category=session_obj.category,
                question=session_obj.question,
                created_at=session_obj.created_at,
                records=[
                    HistoryRecordOut(
                        record_id=record.id,
                        module=record.module,
                        input_payload=record.input_payload,
                        calc_result=record.calc_result,
                        final_text=record.final_text,
                        created_at=record.created_at,
                    )
                    for record in records
                ],
            )
        )

    return UserHistoryOut(user_id=session.user_id, sessions=session_items)


@router.post("", response_model=UserOut)
def create_user_legacy(payload: UserProfileUpdate, db: Session | None = Depends(get_db)) -> UserOut | User:
    if not settings.db_persistence_enabled:
        return UserOut(
            id=0,
            username="guest",
            nickname=payload.nickname,
            profile_payload=payload.profile_payload,
            created_at=datetime.now(),
        )

    username = f"legacy_{int(datetime.now().timestamp())}"
    user = User(
        username=username,
        nickname=payload.nickname,
        password_hash=hash_password(token := username),
        profile_payload=payload.profile_payload,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
