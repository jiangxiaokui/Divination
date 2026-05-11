from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.user_auth import UserSession, get_optional_user
from app.db.session import get_db
from app.models.divination_record import DivinationRecord
from app.models.divination_session import DivinationSession
from app.models.llm_call_log import LLMCallLog
from app.models.random_trace import RandomTrace
from app.models.user import User
from app.schemas.reading import LotDisplay, LotReadingCreate, ReadingOut, ResultCard
from app.services.llm_service import enhance_reading
from app.services.lot_service import draw_lot

router = APIRouter(prefix="/lots", tags=["lots"])
settings = get_settings()

ALLOWED_LOT_TYPES = {"guanyin", "yuelao", "generic"}


def _short_question(question: str | None, limit: int = 32) -> str | None:
    if not question:
        return None
    compact = " ".join(question.strip().split())
    if not compact:
        return None
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}…"


def _build_user_context(user: User | None, db: Session | None) -> dict | None:
    if user is None or db is None:
        return None

    recent_sessions = db.scalars(
        select(DivinationSession)
        .where(DivinationSession.user_id == user.id)
        .order_by(DivinationSession.created_at.desc(), DivinationSession.id.desc())
        .limit(3)
    ).all()

    return {
        "nickname": user.nickname,
        "profile": user.profile_payload or {},
        "recent_questions": [session.question for session in recent_sessions if session.question],
    }


@router.post("/{lot_type}/reading", response_model=ReadingOut)
def create_lot_reading(
    lot_type: str,
    payload: LotReadingCreate,
    current_user: UserSession | None = Depends(get_optional_user),
    db: Session | None = Depends(get_db),
) -> ReadingOut:
    if lot_type not in ALLOWED_LOT_TYPES:
        raise HTTPException(status_code=400, detail=f"unsupported lot type: {lot_type}")
    if db is None:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    if current_user is not None:
        payload.user_id = current_user.user_id

    user = db.get(User, payload.user_id) if (db is not None and payload.user_id is not None) else None
    user_context = _build_user_context(user, db)

    try:
        lot, trace = draw_lot(db=db, lot_type=lot_type, seed=payload.seed)
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    lot_display = LotDisplay(
        lot_no=lot["lot_no"],
        title=lot["title"],
        poem=lot["poem"],
        meaning=lot["meaning"],
    )
    cards = [
        ResultCard(title="签号", content=f"第{lot_display.lot_no}签 · {lot_display.title}", tone="info"),
        ResultCard(title="签诗", content=lot_display.poem, tone="neutral"),
        ResultCard(title="解签", content=lot_display.meaning, tone="advice"),
    ]
    if payload.question:
        cards.insert(0, ResultCard(title="本次问题聚焦", content=f"你这次最想解决的是: {_short_question(payload.question, 120)}", tone="info"))
    if user_context:
        cards.append(
            ResultCard(
                title="个人上下文参考",
                content="\n".join([
                    f"当前用户: {user_context['nickname']}",
                    f"最近问题: {' / '.join(user_context['recent_questions'][:2])}" if user_context.get("recent_questions") else "最近问题: 暂无",
                ]),
                tone="info",
            )
        )
    headline = "灵签占断"
    summary = f"你抽到了第{lot_display.lot_no}签: {lot_display.title}"
    if payload.question:
        summary = f"{summary} 当前聚焦问题: {_short_question(payload.question, 28)}。"
    if user_context:
        summary = f"{summary} 已参考你的近期使用记录。"
    llm_result = None

    if payload.reading_mode == "deep":
        try:
            llm_result = enhance_reading(
                module=f"lot_{lot_type}",
                question=payload.question,
                summary=summary,
                cards=[c.model_dump() for c in cards],
                user_context=user_context,
            )
            if llm_result and llm_result.content:
                cards.append(ResultCard(title="深度解签", content=llm_result.content, tone="advice"))
                summary = f"{summary} 已生成深度解签。"
        except Exception:
            cards.append(ResultCard(title="深度解签", content="当前无法生成深度解签，已返回极速解签。", tone="info"))

    if payload.user_id is not None:
        user = db.get(User, payload.user_id)
        if user is None:
            raise HTTPException(status_code=404, detail="user not found")

    session = DivinationSession(
        user_id=payload.user_id,
        category=f"lot_{lot_type}",
        question=payload.question,
        client_meta=payload.client_meta,
    )
    db.add(session)
    db.flush()

    user_input = payload.model_dump()
    user_input["lot_type"] = lot_type

    record = DivinationRecord(
        session_id=session.id,
        module=f"lot_{lot_type}",
        input_payload=user_input,
        calc_result={"lot": lot, "cards": [c.model_dump() for c in cards]},
        final_text=summary,
        confidence_level="medium",
    )
    db.add(record)
    db.flush()

    if llm_result is not None:
        llm_log = LLMCallLog(
            record_id=record.id,
            provider="openai-compatible",
            model=settings.openai_model,
            prompt_tokens=llm_result.prompt_tokens,
            completion_tokens=llm_result.completion_tokens,
            latency_ms=llm_result.latency_ms,
            request_payload_masked={"module": f"lot_{lot_type}", "reading_mode": payload.reading_mode},
            response_payload={"content": llm_result.content},
        )
        db.add(llm_log)

    random_trace = RandomTrace(
        record_id=record.id,
        rng_algorithm=trace["rng_algorithm"],
        seed=trace["seed"],
        draw_steps=trace["draw_steps"],
    )
    db.add(random_trace)
    db.commit()
    db.refresh(record)

    return ReadingOut(
        session_id=session.id,
        record_id=record.id,
        module=record.module,
        created_at=record.created_at or datetime.now(),
        headline=headline,
        summary=summary,
        cards=cards,
        lot=lot_display,
    )
