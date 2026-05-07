from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.effective_database_url,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, class_=Session)


def get_db() -> Generator[Session | None, None, None]:
    if not settings.db_persistence_enabled:
        yield None
        return

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
