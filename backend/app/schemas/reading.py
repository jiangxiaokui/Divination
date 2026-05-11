from datetime import datetime
from pydantic import BaseModel, Field


class ReadingCreate(BaseModel):
    user_id: int | None = None
    question: str | None = None
    client_meta: dict | None = None
    reading_mode: str = "fast"
    input_payload: dict = Field(default_factory=dict)


class ResultCard(BaseModel):
    title: str
    content: str
    tone: str = "neutral"


class LotDisplay(BaseModel):
    lot_no: int
    title: str
    poem: str
    meaning: str


class ReadingOut(BaseModel):
    session_id: int
    record_id: int
    module: str
    created_at: datetime
    headline: str
    summary: str
    cards: list[ResultCard] = Field(default_factory=list)
    lot: LotDisplay | None = None


class LotReadingCreate(BaseModel):
    user_id: int | None = None
    question: str | None = None
    client_meta: dict | None = None
    reading_mode: str = "fast"
    input_payload: dict = Field(default_factory=dict)
    seed: int | None = None


class HistoryRecordOut(BaseModel):
    record_id: int
    module: str
    input_payload: dict
    calc_result: dict | None
    final_text: str | None
    created_at: datetime


class SessionHistoryOut(BaseModel):
    session_id: int
    category: str
    question: str | None
    created_at: datetime
    records: list[HistoryRecordOut]


class UserHistoryOut(BaseModel):
    user_id: int
    sessions: list[SessionHistoryOut]
