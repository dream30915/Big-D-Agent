"""Telegram command + message handlers."""
from __future__ import annotations

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import ContextTypes

from src.agent.hermes import handle_message
from src.config import get_settings
from src.core import costguard
from src.core.logging import logger
from src.db import repository
from src.db.repository import counts_for_admin, log_task, upsert_user
from src.llm import credits
from src.llm.openrouter import llm_client
from src.scheduler import service as scheduler
from src.scheduler.parse import SpecError, describe, parse_spec

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
    "*ตั้งเวลาอัตโนมัติ:*\n"
    "/schedule `<เวลา> | <คำสั่ง>` — ตั้งงานซ้ำ\n"
    "   เช่น `/schedule daily 09:00 | สรุปข่าว AI วันนี้`\n"
    "   หรือ `/schedule every 30m | เช็คราคาทองคำ`\n"
    "   หรือ `/schedule cron 0 9 * * 1 | รายงานประจำสัปดาห์`\n"
    "/schedules — ดูงานที่ตั้งไว้\n"
    "/unschedule `<id>` — ยกเลิกงาน\n\n"
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


async def schedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = get_settings()
    if not settings.enable_scheduler:
        await update.message.reply_text("ระบบตั้งเวลาปิดอยู่ / scheduler is disabled.")
        return
    user = update.effective_user
    chat = update.effective_chat
    raw = (update.message.text or "").partition(" ")[2].strip()
    if "|" not in raw:
        await update.message.reply_markdown(
            "รูปแบบ: `/schedule <เวลา> | <คำสั่ง>`\n"
            "เช่น `/schedule daily 09:00 | สรุปข่าว AI วันนี้`"
        )
        return
    spec_part, _, prompt = raw.partition("|")
    prompt = prompt.strip()
    if not prompt:
        await update.message.reply_text("ใส่คำสั่งหลัง | ด้วยครับ / add a task after '|'.")
        return
    try:
        trigger_type, trigger_arg = parse_spec(spec_part)
    except SpecError as exc:
        await update.message.reply_text(f"❌ {exc}")
        return

    if await repository.count_active_schedules(user.id) >= settings.max_schedules_per_user:
        await update.message.reply_text(
            f"ตั้งได้สูงสุด {settings.max_schedules_per_user} งาน — ลบของเก่าด้วย /unschedule ก่อน"
        )
        return

    row = await repository.add_schedule(user.id, chat.id, prompt, trigger_type, trigger_arg)
    if row is None:
        await update.message.reply_text("บันทึกไม่สำเร็จ (ตรวจการเชื่อมต่อฐานข้อมูล) / DB unavailable.")
        return
    scheduler.add(row)
    await update.message.reply_markdown(
        f"✅ ตั้งงาน #{row.id} แล้ว — {describe(trigger_type, trigger_arg)}\n`{prompt[:120]}`"
    )


async def schedules_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    rows = await repository.list_schedules(update.effective_user.id)
    if not rows:
        await update.message.reply_text("ยังไม่มีงานที่ตั้งไว้ / no schedules yet.")
        return
    lines = [
        f"#{r.id} · {describe(r.trigger_type, r.trigger_arg)} · {r.prompt[:60]}" for r in rows
    ]
    await update.message.reply_text("🗓️ งานที่ตั้งไว้:\n" + "\n".join(lines))


async def unschedule_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = context.args if hasattr(context, "args") else []
    if not args or not args[0].isdigit():
        await update.message.reply_text("ใช้: /unschedule <id> (ดู id จาก /schedules)")
        return
    schedule_id = int(args[0])
    ok = await repository.deactivate_schedule(schedule_id, update.effective_user.id)
    if ok:
        scheduler.remove(schedule_id)
        await update.message.reply_text(f"🗑️ ยกเลิกงาน #{schedule_id} แล้ว")
    else:
        await update.message.reply_text(f"ไม่พบงาน #{schedule_id} ของคุณ / not found.")


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
