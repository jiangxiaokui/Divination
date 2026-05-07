from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RandomTrace(Base):
    __tablename__ = "random_traces"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(ForeignKey("divination_records.id"), nullable=False, unique=True)
    rng_algorithm: Mapped[str] = mapped_column(String(64), nullable=False)
    seed: Mapped[str] = mapped_column(String(128), nullable=False)
    draw_steps: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), nullable=False, server_default=func.now()
    )

    record = relationship("DivinationRecord", back_populates="random_trace")
