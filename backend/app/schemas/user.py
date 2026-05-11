from datetime import datetime
from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    nickname: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    profile_payload: dict | None = None


class UserLogin(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class UserProfileUpdate(BaseModel):
    nickname: str = Field(min_length=1, max_length=64)
    profile_payload: dict | None = None


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str
    profile_payload: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserOut
