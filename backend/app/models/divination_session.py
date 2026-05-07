from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DivinationSession(Base):
    __tablename__ = "divination_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    question: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    user = relationship("User", back_populates="sessions")
    records = relationship("DivinationRecord", back_populates="session", cascade="all, delete-orphan")
