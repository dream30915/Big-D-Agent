"""Telegram command + message handlers."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.agent.hermes import handle_message
from src.core.logging import logger
from src.db.repository import log_task, upsert_user

_WELCOME = (
    "🤖 *Big-D-Agent* พร้อมใช้งาน!\n\n"
    "ส่งข้อความอะไรมาก็ได้ — ผมจะจัดประเภทงานแล้วช่วยจัดการให้:\n"
    "• ส่งลิงก์ → ดึง/สรุปเนื้อหาเว็บ\n"
    "• \"เขียนแคปชั่น...\" → สร้างคอนเทนต์\n"
    "• \"วิเคราะห์...\" → วิเคราะห์ธุรกิจ/ข้อมูล\n"
    "• คำถามทั่วไป → ตอบด้วย AI\n\n"
    "พิมพ์ /help เพื่อดูคำสั่งทั้งหมด"
)

_HELP = (
    "*คำสั่ง:*\n"
    "/start — เริ่มต้น / ข้อความต้อนรับ\n"
    "/help — วิธีใช้\n"
    "/ping — ตรวจว่าบอทยังตอบอยู่ไหม\n\n"
    "หรือพิมพ์คุยได้เลย — ผมเลือกทักษะ (scrape/content/analyze/support) ให้อัตโนมัติ"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        await upsert_user(user.id, user.username)
    await update.message.reply_markdown(_WELCOME)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_markdown(_HELP)


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("pong ✅")


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text
    user = update.effective_user

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action=ChatAction.TYPING
    )
    reply = await handle_message(text)
    logger.info("handled intent={} skill={}", reply.intent.value, reply.skill)

    if user:
        await log_task(user.id, reply.intent.value, reply.skill, text)

    # Telegram caps messages at 4096 chars.
    await update.message.reply_text(reply.text[:4096])
