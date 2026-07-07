"""Thin persistence helpers used by the bot. All are no-ops-on-failure so a DB
outage never breaks a chat reply."""
from __future__ import annotations

from sqlalchemy import select

from src.core.logging import logger
from src.db.database import SessionLocal
from src.db.models import Task, User


async def upsert_user(telegram_id: int, username: str | None) -> None:
    try:
        async with SessionLocal() as session:
            existing = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if existing is None:
                session.add(User(telegram_id=telegram_id, username=username))
                await session.commit()
    except Exception as exc:
        logger.debug("upsert_user skipped: {}", exc)


async def log_task(telegram_id: int, intent: str, skill: str | None, prompt: str) -> None:
    try:
        async with SessionLocal() as session:
            user = await session.scalar(
                select(User).where(User.telegram_id == telegram_id)
            )
            if user is None:
                user = User(telegram_id=telegram_id, username=None)
                session.add(user)
                await session.flush()
            session.add(
                Task(user_id=user.id, intent=intent, skill=skill, prompt=prompt[:2000])
            )
            await session.commit()
    except Exception as exc:
        logger.debug("log_task skipped: {}", exc)
