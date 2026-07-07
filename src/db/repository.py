"""Thin persistence helpers used by the bot. All are no-ops-on-failure so a DB
outage never breaks a chat reply."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update

from src.core.logging import logger
from src.db.database import SessionLocal
from src.db.models import Schedule, Task, User


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


async def add_schedule(
    telegram_id: int, chat_id: int, prompt: str, trigger_type: str, trigger_arg: str
) -> Schedule | None:
    """Persist a schedule; returns the row (with id) or None if the DB is down."""
    try:
        async with SessionLocal() as session:
            row = Schedule(
                telegram_id=telegram_id,
                chat_id=chat_id,
                prompt=prompt[:2000],
                trigger_type=trigger_type,
                trigger_arg=trigger_arg,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return row
    except Exception as exc:
        logger.debug("add_schedule failed: {}", exc)
        return None


async def list_schedules(telegram_id: int) -> list[Schedule]:
    try:
        async with SessionLocal() as session:
            rows = await session.scalars(
                select(Schedule)
                .where(Schedule.telegram_id == telegram_id, Schedule.active.is_(True))
                .order_by(Schedule.id)
            )
            return list(rows)
    except Exception as exc:
        logger.debug("list_schedules failed: {}", exc)
        return []


async def count_active_schedules(telegram_id: int) -> int:
    try:
        async with SessionLocal() as session:
            n = await session.scalar(
                select(func.count())
                .select_from(Schedule)
                .where(Schedule.telegram_id == telegram_id, Schedule.active.is_(True))
            )
            return int(n or 0)
    except Exception as exc:
        logger.debug("count_active_schedules failed: {}", exc)
        return 0


async def get_schedule(schedule_id: int) -> Schedule | None:
    try:
        async with SessionLocal() as session:
            return await session.get(Schedule, schedule_id)
    except Exception as exc:
        logger.debug("get_schedule failed: {}", exc)
        return None


async def all_active_schedules() -> list[Schedule]:
    try:
        async with SessionLocal() as session:
            rows = await session.scalars(select(Schedule).where(Schedule.active.is_(True)))
            return list(rows)
    except Exception as exc:
        logger.debug("all_active_schedules failed: {}", exc)
        return []


async def deactivate_schedule(schedule_id: int, telegram_id: int) -> bool:
    """Soft-delete a schedule owned by telegram_id. Returns True if one changed."""
    try:
        async with SessionLocal() as session:
            result = await session.execute(
                update(Schedule)
                .where(
                    Schedule.id == schedule_id,
                    Schedule.telegram_id == telegram_id,
                    Schedule.active.is_(True),
                )
                .values(active=False)
            )
            await session.commit()
            return result.rowcount > 0
    except Exception as exc:
        logger.debug("deactivate_schedule failed: {}", exc)
        return False


async def touch_schedule_run(schedule_id: int) -> None:
    try:
        async with SessionLocal() as session:
            await session.execute(
                update(Schedule)
                .where(Schedule.id == schedule_id)
                .values(last_run=datetime.now(timezone.utc))
            )
            await session.commit()
    except Exception as exc:
        logger.debug("touch_schedule_run failed: {}", exc)


async def counts_for_admin() -> dict[str, int]:
    """User + task totals for /stats. Returns zeros if the DB is unavailable."""
    try:
        async with SessionLocal() as session:
            users = await session.scalar(select(func.count()).select_from(User)) or 0
            tasks = await session.scalar(select(func.count()).select_from(Task)) or 0
            return {"users": int(users), "tasks": int(tasks)}
    except Exception as exc:
        logger.debug("counts_for_admin skipped: {}", exc)
        return {"users": 0, "tasks": 0}
