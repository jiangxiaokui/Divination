from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AdminRecordQueryMode = Literal[
    "all",
    "has_name",
    "has_question",
    "has_name_or_question",
    "has_name_and_question",
]


class AdminLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class AdminLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    advanced_query_enabled: bool


class AdminRecordItem(BaseModel):
    record_id: int
    session_id: int
    module: str
    category: str
    display_name: str | None
    has_name: bool
    question: str | None
    has_question: bool
    user_id: int | None
    session_created_at: datetime
    created_at: datetime
    has_user: bool
    confidence_level: str | None
    has_calc_result: bool
    has_random_trace: bool
    llm_call_count: int
    input_payload: dict
    calc_result: dict | None
    final_text: str | None
    client_meta: dict | None


class AdminModuleSummaryItem(BaseModel):
    module: str
    count: int


class AdminRecordSummary(BaseModel):
    query_mode: AdminRecordQueryMode
    total_records: int
    filtered_records: int
    returned_records: int
    with_user_count: int
    anonymous_count: int
    with_name_count: int
    with_question_count: int
    modules: list[AdminModuleSummaryItem]


class AdminRecordListResponse(BaseModel):
    limit: int
    offset: int
    total: int
    summary: AdminRecordSummary
    items: list[AdminRecordItem]


class AdminRuntimeStatusResponse(BaseModel):
    db_persistence_enabled: bool
    app_env: str
    advanced_query_enabled: bool
