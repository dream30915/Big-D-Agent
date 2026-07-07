"""Async engine + session factory, and a best-effort schema initialiser.

The bot runs even if Postgres is down (persistence is non-fatal for a chat
reply), so init_db logs and continues on failure rather than crashing startup.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import get_settings
from src.core.logging import logger
from src.db.models import Base

_settings = get_settings()
engine = create_async_engine(_settings.database_url, echo=False, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> bool:
    """Create tables if they don't exist. Returns True on success."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database schema ready")
        return True
    except Exception as exc:  # broad on purpose — DB is optional at startup
        logger.warning("database unavailable ({}); continuing without persistence", exc)
        return False
