"""Scheduler service — runs saved schedules and delivers results via Telegram.

Built on APScheduler's AsyncIOScheduler so jobs share the app's event loop.
Schedules are persisted in Postgres (source of truth); APScheduler holds the
in-memory jobs and is repopulated from the DB on startup. Each job runs its
prompt through Hermes (so cost guard / budget / memory all apply) and delivers
the reply through a caller-supplied `deliver(chat_id, text)` coroutine.
"""
from __future__ import annotations

from typing import Awaitable, Callable

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from src.agent.hermes import handle_message
from src.config import get_settings
from src.core.logging import logger
from src.db import repository
from src.db.models import Schedule

Deliver = Callable[[int, str], Awaitable[None]]

_scheduler: AsyncIOScheduler | None = None
_deliver: Deliver | None = None


def _job_id(schedule_id: int) -> str:
    return f"sched:{schedule_id}"


def _trigger_for(row: Schedule):
    tz = get_settings().scheduler_timezone
    if row.trigger_type == "interval":
        return IntervalTrigger(seconds=int(row.trigger_arg), timezone=tz)
    if row.trigger_type == "daily":
        hh, mm = row.trigger_arg.split(":")
        return CronTrigger(hour=int(hh), minute=int(mm), timezone=tz)
    if row.trigger_type == "cron":
        return CronTrigger.from_crontab(row.trigger_arg, timezone=tz)
    raise ValueError(f"unknown trigger_type: {row.trigger_type}")


async def start(deliver: Deliver) -> None:
    """Start the scheduler and reload persisted schedules."""
    global _scheduler, _deliver
    _deliver = deliver
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone=get_settings().scheduler_timezone)
    if not _scheduler.running:
        _scheduler.start()
    reloaded = 0
    for row in await repository.all_active_schedules():
        try:
            _add_job(row)
            reloaded += 1
        except Exception as exc:
            logger.warning("could not reload schedule {}: {}", row.id, exc)
    logger.info("scheduler started ({} schedule(s) reloaded)", reloaded)


async def shutdown() -> None:
    if _scheduler is not None and _scheduler.running:
        _scheduler.shutdown(wait=False)


def _add_job(row: Schedule) -> None:
    assert _scheduler is not None
    _scheduler.add_job(
        _run_schedule,
        trigger=_trigger_for(row),
        args=[row.id],
        id=_job_id(row.id),
        replace_existing=True,
        misfire_grace_time=300,
    )


def add(row: Schedule) -> None:
    """Register a job for a freshly-created schedule row."""
    if _scheduler is None:
        logger.warning("scheduler not started; schedule {} not registered", row.id)
        return
    _add_job(row)


def remove(schedule_id: int) -> None:
    if _scheduler is None:
        return
    try:
        _scheduler.remove_job(_job_id(schedule_id))
    except Exception:
        pass  # job may not exist (e.g. never loaded) — harmless


async def _run_schedule(schedule_id: int) -> None:
    """Execute one schedule: re-read it, run through Hermes, deliver the reply."""
    row = await repository.get_schedule(schedule_id)
    if row is None or not row.active:
        remove(schedule_id)
        return
    logger.info("running schedule {} for user {}", schedule_id, row.telegram_id)
    try:
        reply = await handle_message(row.prompt, user_id=row.telegram_id)
        if _deliver is not None:
            header = "⏰ *งานตามเวลา / Scheduled task*\n"
            await _deliver(row.chat_id, header + reply.text)
        await repository.touch_schedule_run(schedule_id)
    except Exception as exc:
        logger.error("schedule {} failed: {}", schedule_id, exc)
