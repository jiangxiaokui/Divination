"""
知识库 API：提供知识条目的查询、新增、更新接口（管理员才能写，所有人可读）。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.knowledge_base import KnowledgeBase
from app.services import kb_service

router = APIRouter(prefix="/kb", tags=["knowledge_base"])


class KBEntryOut(BaseModel):
    id: int
    module: str
    category: str
    keyword: str
    content: str
    source: str

    model_config = {"from_attributes": True}


class KBEntryIn(BaseModel):
    module: str
    category: str
    keyword: str
    content: str
    source: str = "manual"


@router.get("/", response_model=list[KBEntryOut])
def list_kb(
    module: str | None = Query(None),
    category: str | None = Query(None),
    keyword: str | None = Query(None),
    limit: int = Query(50, le=200),
    db: Session | None = Depends(get_db),
) -> list[KBEntryOut]:
    if db is None:
        return []
    q = db.query(KnowledgeBase)
    if module:
        q = q.filter(KnowledgeBase.module == module)
    if category:
        q = q.filter(KnowledgeBase.category == category)
    if keyword:
        q = q.filter(KnowledgeBase.keyword.contains(keyword))
    return q.limit(limit).all()


@router.post("/", response_model=KBEntryOut, status_code=201)
def create_or_update_kb(payload: KBEntryIn, db: Session | None = Depends(get_db)) -> KBEntryOut:
    if db is None:
        raise HTTPException(status_code=503, detail="数据库未启用")
    return kb_service.upsert_entry(
        db=db,
        module=payload.module,
        category=payload.category,
        keyword=payload.keyword,
        content=payload.content,
        source=payload.source,
    )


@router.delete("/{entry_id}", response_model=None)
def delete_kb(entry_id: int, db: Session | None = Depends(get_db)) -> Response:
    if db is None:
        raise HTTPException(status_code=503, detail="数据库未启用")
    row = db.get(KnowledgeBase, entry_id)
    if row is None:
        raise HTTPException(status_code=404, detail="条目不存在")
    db.delete(row)
    db.commit()
    return Response(status_code=204)
