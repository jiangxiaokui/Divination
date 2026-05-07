from datetime import datetime
from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    nickname: str = Field(min_length=1, max_length=64)
    profile_payload: dict | None = None


class UserOut(BaseModel):
    id: int
    nickname: str
    profile_payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
