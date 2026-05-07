from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


@router.post("", response_model=UserOut)
def create_user(payload: UserCreate, db: Session | None = Depends(get_db)) -> UserOut | User:
    if not settings.db_persistence_enabled:
        return UserOut(
            id=0,
            nickname=payload.nickname,
            profile_payload=payload.profile_payload,
            created_at=datetime.now(),
        )

    user = User(nickname=payload.nickname, profile_payload=payload.profile_payload)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
