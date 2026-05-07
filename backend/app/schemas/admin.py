from datetime import datetime
from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime


class AdminRecordItem(BaseModel):
    record_id: int
    session_id: int
    module: str
    question: str | None
    created_at: datetime
    has_user: bool


class AdminRecordListResponse(BaseModel):
    total: int
    items: list[AdminRecordItem]


class AdminRuntimeStatusResponse(BaseModel):
    db_persistence_enabled: bool
    app_env: str
