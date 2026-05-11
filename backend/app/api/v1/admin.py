from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.admin_auth import (
    AdminSession,
    authenticate_admin,
    issue_admin_token,
    require_admin,
    revoke_admin_token,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.models.divination_record import DivinationRecord
from app.models.divination_session import DivinationSession
from app.models.llm_call_log import LLMCallLog
from app.models.random_trace import RandomTrace
from app.schemas.admin import (
    AdminLoginRequest,
    AdminLoginResponse,
    AdminModuleSummaryItem,
    AdminRecordItem,
    AdminRecordListResponse,
    AdminRecordQueryMode,
    AdminRecordSummary,
    AdminRuntimeStatusResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])
settings = get_settings()


def _normalize_text(value: object) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _extract_display_name(input_payload: dict | None) -> str | None:
    payload = input_payload or {}

    for key in ("full_name", "fullName", "name"):
        name = _normalize_text(payload.get(key))
        if name:
            return name

    person_a = _normalize_text(payload.get("person_a"))
    person_b = _normalize_text(payload.get("person_b"))
    if person_a and person_b:
        return f"{person_a} x {person_b}"

    return person_a or person_b


def _build_record_item(
    record: DivinationRecord,
    session: DivinationSession,
    random_trace_id: int | None,
    llm_call_count: int,
) -> AdminRecordItem:
    display_name = _extract_display_name(record.input_payload)
    question = _normalize_text(session.question)
    return AdminRecordItem(
        record_id=record.id,
        session_id=session.id,
        module=record.module,
        category=session.category,
        display_name=display_name,
        has_name=display_name is not None,
        question=question,
        has_question=question is not None,
        user_id=session.user_id,
        session_created_at=session.created_at,
        created_at=record.created_at,
        has_user=session.user_id is not None,
        confidence_level=record.confidence_level,
        has_calc_result=record.calc_result is not None,
        has_random_trace=random_trace_id is not None,
        llm_call_count=llm_call_count,
        input_payload=record.input_payload,
        calc_result=record.calc_result,
        final_text=record.final_text,
        client_meta=session.client_meta,
    )


def _match_query_mode(item: AdminRecordItem, query_mode: AdminRecordQueryMode) -> bool:
    if query_mode == "all":
        return True
    if query_mode == "has_name":
        return item.has_name
    if query_mode == "has_question":
        return item.has_question
    if query_mode == "has_name_or_question":
        return item.has_name or item.has_question
    return item.has_name and item.has_question


def _build_runtime_status(session: AdminSession) -> AdminRuntimeStatusResponse:
    return AdminRuntimeStatusResponse(
        db_persistence_enabled=settings.db_persistence_enabled,
        app_env=settings.app_env,
        advanced_query_enabled=session.advanced_query_enabled,
    )


def _fetch_admin_records(
    limit: int,
    offset: int,
    query_mode: AdminRecordQueryMode,
    session: AdminSession,
    db: Session | None,
) -> AdminRecordListResponse:
    if not settings.db_persistence_enabled or db is None:
        raise HTTPException(status_code=503, detail="database persistence is disabled")

    if not session.advanced_query_enabled and query_mode != "all":
        raise HTTPException(status_code=403, detail="当前账号仅支持默认查询")

    total_stmt = select(func.count()).select_from(DivinationRecord)
    total_records = db.execute(total_stmt).scalar_one()

    llm_count_subquery = (
        select(LLMCallLog.record_id, func.count(LLMCallLog.id).label("llm_call_count"))
        .group_by(LLMCallLog.record_id)
        .subquery()
    )

    base_stmt = (
        select(
            DivinationRecord,
            DivinationSession,
            RandomTrace.id.label("random_trace_id"),
            func.coalesce(llm_count_subquery.c.llm_call_count, 0).label("llm_call_count"),
        )
        .join(DivinationSession, DivinationSession.id == DivinationRecord.session_id)
        .outerjoin(RandomTrace, RandomTrace.record_id == DivinationRecord.id)
        .outerjoin(llm_count_subquery, llm_count_subquery.c.record_id == DivinationRecord.id)
        .order_by(DivinationRecord.created_at.desc(), DivinationRecord.id.desc())
    )

    if query_mode == "all":
        rows = db.execute(base_stmt.limit(limit).offset(offset)).all()
        items = [
            _build_record_item(record, session, random_trace_id, llm_call_count)
            for record, session, random_trace_id, llm_call_count in rows
        ]
        filtered_total = total_records
    else:
        rows = db.execute(base_stmt).all()
        filtered_items = [
            _build_record_item(record, session, random_trace_id, llm_call_count)
            for record, session, random_trace_id, llm_call_count in rows
        ]
        filtered_items = [item for item in filtered_items if _match_query_mode(item, query_mode)]
        filtered_total = len(filtered_items)
        items = filtered_items[offset : offset + limit]

    module_counter = Counter(item.module for item in items)
    summary = AdminRecordSummary(
        query_mode=query_mode,
        total_records=total_records,
        filtered_records=filtered_total,
        returned_records=len(items),
        with_user_count=sum(1 for item in items if item.has_user),
        anonymous_count=sum(1 for item in items if not item.has_user),
        with_name_count=sum(1 for item in items if item.has_name),
        with_question_count=sum(1 for item in items if item.has_question),
        modules=[
            AdminModuleSummaryItem(module=module, count=count)
            for module, count in module_counter.most_common()
        ],
    )

    return AdminRecordListResponse(
        limit=limit,
        offset=offset,
        total=filtered_total,
        summary=summary,
        items=items,
    )


@router.post("/login", response_model=AdminLoginResponse)
def admin_login(payload: AdminLoginRequest) -> AdminLoginResponse:
    advanced_query_enabled = authenticate_admin(payload.username, payload.password)
    if advanced_query_enabled is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    token, expires_at = issue_admin_token(advanced_query_enabled=advanced_query_enabled)
    return AdminLoginResponse(
        access_token=token,
        expires_at=expires_at,
        advanced_query_enabled=advanced_query_enabled,
    )


@router.post("/logout")
def admin_logout(session: AdminSession = Depends(require_admin)) -> dict:
    revoke_admin_token(session.token)
    return {"ok": True}


@router.get("/runtime", response_model=AdminRuntimeStatusResponse)
def admin_runtime_status(session: AdminSession = Depends(require_admin)) -> AdminRuntimeStatusResponse:
    return _build_runtime_status(session)


@router.get("/records", response_model=AdminRecordListResponse)
def admin_records(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    query_mode: AdminRecordQueryMode = Query(default="all"),
    session: AdminSession = Depends(require_admin),
    db: Session | None = Depends(get_db),
) -> AdminRecordListResponse:
    return _fetch_admin_records(limit=limit, offset=offset, query_mode=query_mode, session=session, db=db)
