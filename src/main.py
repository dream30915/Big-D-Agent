"""Entrypoint — runs the FastAPI service and the Telegram bot together.

Both share one asyncio loop:
  * uvicorn serves the API/health endpoint on API_PORT.
  * python-telegram-bot long-polls for updates.

If TELEGRAM_BOT_TOKEN is not set, the API still starts (so /health and /agent
work) and a warning is logged — handy for local testing before you have a token.
"""
from __future__ import annotations

import asyncio
import contextlib

import uvicorn

from src.api.app import app
from src.config import get_settings
from src.core.logging import logger, setup_logging
from src.db.database import init_db


async def _serve_api(host: str, port: int) -> None:
    config = uvicorn.Config(app, host=host, port=port, log_level="info", loop="asyncio")
    server = uvicorn.Server(config)
    await server.serve()


async def _run_bot() -> None:
    # Imported here so the API can start even if telegram deps hiccup.
    from src.bot.telegram_bot import build_application
    from src.scheduler import service as scheduler

    settings = get_settings()
    application = build_application()
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot is polling")

    # Start the scheduler once the bot can deliver results.
    if settings.enable_scheduler:
        async def deliver(chat_id: int, text: str) -> None:
            await application.bot.send_message(chat_id=chat_id, text=text[:4096])

        await scheduler.start(deliver)

    # Block forever; cancellation on shutdown stops the updater cleanly.
    try:
        await asyncio.Event().wait()
    finally:
        with contextlib.suppress(Exception):
            await scheduler.shutdown()
            await application.updater.stop()
            await application.stop()
            await application.shutdown()


async def _main() -> None:
    setup_logging()
    settings = get_settings()
    logger.info("starting Big-D-Agent (env={})", settings.environment)

    await init_db()

    tasks = [asyncio.create_task(_serve_api(settings.api_host, settings.api_port))]

    if settings.telegram_configured:
        tasks.append(asyncio.create_task(_run_bot()))
    else:
        logger.warning(
            "TELEGRAM_BOT_TOKEN not configured — API only. Set it in .env to enable the bot."
        )

    await asyncio.gather(*tasks)


def main() -> None:
    try:
        asyncio.run(_main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("shutting down")


if __name__ == "__main__":
    main()
