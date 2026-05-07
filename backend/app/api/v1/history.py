from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.admin_auth import require_admin
from app.core.config import get_settings
from app.db.session import get_db
from app.models.divination_record import DivinationRecord
from app.models.divination_session import DivinationSession
from app.schemas.reading import HistoryRecordOut, SessionHistoryOut

router = APIRouter(prefix="/history", tags=["history"])
settings = get_settings()


@router.get("/session/{session_id}", response_model=SessionHistoryOut)
def get_session_history(
    session_id: int,
    _: str = Depends(require_admin),
    db: Session | None = Depends(get_db),
) -> SessionHistoryOut:

    if not settings.db_persistence_enabled:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    session_obj = db.get(DivinationSession, session_id)
    if session_obj is None:
        raise HTTPException(status_code=404, detail="session not found")

    records = db.scalars(
        select(DivinationRecord)
        .where(DivinationRecord.session_id == session_id)
        .order_by(DivinationRecord.created_at.asc(), DivinationRecord.id.asc())
    ).all()

    return SessionHistoryOut(
        session_id=session_obj.id,
        category=session_obj.category,
        question=session_obj.question,
        created_at=session_obj.created_at,
        records=[
            HistoryRecordOut(
                record_id=r.id,
                module=r.module,
                input_payload=r.input_payload,
                calc_result=r.calc_result,
                final_text=r.final_text,
                created_at=r.created_at,
            )
            for r in records
        ],
    )
