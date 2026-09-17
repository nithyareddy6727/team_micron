from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from .config import settings


_engine: Engine | None = None


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        conn = (
            f"mysql+pymysql://{settings.mysql_user}:{settings.mysql_password}"
            f"@{settings.mysql_host}:{settings.mysql_port}/{settings.mysql_database}"
            "?charset=utf8mb4"
        )
        _engine = create_engine(conn, pool_pre_ping=True)
    return _engine


def check_db() -> bool:
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True
