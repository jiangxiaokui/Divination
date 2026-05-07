"""
知识库 service：从数据库查询玄学知识条目，供各模块解读时优先使用。
"""
from __future__ import annotations

from typing import Optional
from sqlalchemy.orm import Session

from app.models.knowledge_base import KnowledgeBase


def get_entries(
    db: Session,
    module: str,
    category: str | None = None,
    keyword: str | None = None,
    limit: int = 10,
) -> list[KnowledgeBase]:
    """按模块/类别/关键词查询知识库，返回最多 limit 条。"""
    q = db.query(KnowledgeBase).filter(KnowledgeBase.module == module)
    if category:
        q = q.filter(KnowledgeBase.category == category)
    if keyword:
        q = q.filter(KnowledgeBase.keyword.contains(keyword))
    return q.limit(limit).all()


def get_content(
    db: Session,
    module: str,
    category: str,
    keyword: str,
    fallback: str = "",
) -> str:
    """精确匹配模块+类别+关键词，返回 content；未命中返回 fallback。"""
    row = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.module == module,
            KnowledgeBase.category == category,
            KnowledgeBase.keyword == keyword,
        )
        .first()
    )
    return row.content if row else fallback


def search_content(db: Session, module: str, keyword: str) -> str:
    """模糊搜索模块内含有 keyword 的条目，返回第一条 content。"""
    row = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.module == module,
            KnowledgeBase.keyword.contains(keyword),
        )
        .first()
    )
    return row.content if row else ""


def upsert_entry(
    db: Session,
    module: str,
    category: str,
    keyword: str,
    content: str,
    source: str = "builtin",
) -> KnowledgeBase:
    """存在则更新内容，不存在则新增。"""
    row = (
        db.query(KnowledgeBase)
        .filter(
            KnowledgeBase.module == module,
            KnowledgeBase.category == category,
            KnowledgeBase.keyword == keyword,
        )
        .first()
    )
    if row:
        row.content = content
        row.source = source
    else:
        row = KnowledgeBase(
            module=module,
            category=category,
            keyword=keyword,
            content=content,
            source=source,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return row
