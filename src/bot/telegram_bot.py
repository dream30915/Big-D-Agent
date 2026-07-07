"""Build the python-telegram-bot Application with all handlers registered."""
from __future__ import annotations

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from src.bot.handlers import help_command, on_message, ping, start
from src.config import get_settings


def build_application() -> Application:
    settings = get_settings()
    if not settings.telegram_configured:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN is not configured — set it in .env (from @BotFather)."
        )
    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    return app
