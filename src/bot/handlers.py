"""Telegram command + message handlers."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.agent.hermes import handle_message
from src.config import get_settings
from src.core import costguard
from src.core.logging import logger
from src.db.repository import counts_for_admin, log_task, upsert_user
from src.llm import credits
from src.llm.openrouter import llm_client

_WELCOME = (
    "🤖 *Big-D-Agent* พร้อมใช้งาน!\n\n"
    "ส่งข้อความอะไรมาก็ได้ — ผมจะจัดประเภทงานแล้วช่วยจัดการให้:\n"
    "• ส่งลิงก์ → ดึง/สรุปเนื้อหาเว็บ\n"
    "• \"เขียนแคปชั่น...\" → สร้างคอนเทนต์\n"
    "• \"วิเคราะห์...\" → วิเคราะห์ธุรกิจ/ข้อมูล\n"
    "• คำถามทั่วไป → ตอบด้วย AI (จำบทสนทนาล่าสุดได้)\n\n"
    "พิมพ์ /help เพื่อดูคำสั่งทั้งหมด"
)

_HELP = (
    "*คำสั่ง:*\n"
    "/start — เริ่มต้น / ข้อความต้อนรับ\n"
    "/help — วิธีใช้\n"
    "/ping — ตรวจว่าบอทยังตอบอยู่ไหม\n\n"
    "*เฉพาะแอดมิน:*\n"
    "/stats — สถิติการใช้งาน\n"
    "/budget — งบ AI วันนี้\n"
    "/credit — เครดิต OpenRouter คงเหลือ\n\n"
    "หรือพิมพ์คุยได้เลย — ผมเลือกทักษะ (scrape/content/analyze/support) ให้อัตโนมัติ"
)


def _is_admin(update: Update) -> bool:
    admin_id = get_settings().telegram_admin_id
    user = update.effective_user
    return bool(admin_id) and user is not None and user.id == admin_id


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        await upsert_user(user.id, user.username)
    await update.message.reply_markdown(_WELCOME)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(_HELP)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("pong ✅")


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("คำสั่งนี้เฉพาะแอดมิน / admin only.")
        return
    db = await counts_for_admin()
    u = llm_client.usage
    budget = await costguard.snapshot()
    await update.message.reply_markdown(
        "*📊 สถิติ Big-D-Agent*\n"
        f"users: `{db['users']}` · tasks: `{db['tasks']}`\n"
        f"LLM requests (since boot): `{u.requests}` · tokens: `{u.total_tokens}`\n"
        f"งบวันนี้: tokens `{budget['tokens']}/{budget['token_budget']}` · "
        f"${budget['cost_usd']}/${budget['cost_budget_usd']}"
    )


async def budget(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("คำสั่งนี้เฉพาะแอดมิน / admin only.")
        return
    b = await costguard.snapshot()
    await update.message.reply_markdown(
        f"*💰 งบ AI วันนี้ ({b['date']})*\n"
        f"tokens: `{b['tokens']}/{b['token_budget']}`\n"
        f"cost: `${b['cost_usd']}/${b['cost_budget_usd']}`"
    )


async def credit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_admin(update):
        await update.message.reply_text("คำสั่งนี้เฉพาะแอดมิน / admin only.")
        return
    remaining = await credits.remaining_usd()
    if remaining is None:
        await update.message.reply_text("เช็คเครดิตไม่ได้ (ตรวจ OPENROUTER_API_KEY) / can't read credit.")
    else:
        await update.message.reply_text(f"💳 OpenRouter credit: ${remaining:.4f}")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text
    user = update.effective_user

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    reply = await handle_message(text, user_id=user.id if user else None)
    logger.info(
        "handled intent={} skill={} blocked={}",
        reply.intent.value,
        reply.skill,
        reply.blocked,
    )

    if user and not reply.blocked:
        await log_task(user.id, reply.intent.value, reply.skill, text)

    # Telegram caps messages at 4096 chars.
    await update.message.reply_text(reply.text[:4096])
