"""
一键导入知识库初始数据。
用法：在 backend/ 目录下执行：
    python -m app.scripts.seed_kb
"""
import sys
from pathlib import Path

# 确保 backend/ 在 sys.path 中（从任意目录运行均可）
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.db.session import SessionLocal
from app.models.knowledge_base import KnowledgeBase  # noqa: F401 ensure table registered
from app.db.base import Base
from app.db.session import engine
from app.services.kb_seed_data import SEED_DATA


def seed() -> None:
    # 建表（如果不存在）
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    inserted = 0
    skipped = 0
    try:
        for item in SEED_DATA:
            exists = (
                db.query(KnowledgeBase)
                .filter(
                    KnowledgeBase.module == item["module"],
                    KnowledgeBase.category == item["category"],
                    KnowledgeBase.keyword == item["keyword"],
                )
                .first()
            )
            if exists:
                skipped += 1
                continue
            db.add(KnowledgeBase(**item))
            inserted += 1
        db.commit()
        print(f"[seed_kb] 导入完成：新增 {inserted} 条，跳过重复 {skipped} 条，共 {len(SEED_DATA)} 条。")
    except Exception as exc:
        db.rollback()
        print(f"[seed_kb] 导入失败：{exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
