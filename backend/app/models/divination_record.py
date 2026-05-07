from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DivinationRecord(Base):
    __tablename__ = "divination_records"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("divination_sessions.id"), nullable=False)
    module: Mapped[str] = mapped_column(String(64), nullable=False)

    # All user-filled fields are persisted here.
    input_payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    calc_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    final_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence_level: Mapped[str | None] = mapped_column(String(16), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    session = relationship("DivinationSession", back_populates="records")
    random_trace = relationship("RandomTrace", back_populates="record", uselist=False, cascade="all, delete-orphan")
    llm_logs = relationship("LLMCallLog", back_populates="record", cascade="all, delete-orphan")
