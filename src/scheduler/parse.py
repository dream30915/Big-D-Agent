"""Parse a human schedule spec into a (trigger_type, trigger_arg) pair.

Supported forms (case-insensitive):
  every 30m | every 2h | every 1d   -> interval  (arg = seconds)
  daily 09:00                        -> daily     (arg = "HH:MM")
  cron 0 9 * * *                     -> cron      (arg = crontab string)
"""
from __future__ import annotations

import re

_INTERVAL_UNITS = {"m": 60, "h": 3600, "d": 86400}
_MIN_INTERVAL = 60  # seconds


class SpecError(ValueError):
    """Raised when a schedule spec can't be parsed."""


def parse_spec(spec: str) -> tuple[str, str]:
    text = spec.strip().lower()

    if text.startswith("every "):
        m = re.fullmatch(r"(\d+)\s*([mhd])", text[6:].strip())
        if not m:
            raise SpecError("รูปแบบ interval ไม่ถูกต้อง เช่น 'every 30m' / 'every 2h'")
        seconds = int(m.group(1)) * _INTERVAL_UNITS[m.group(2)]
        if seconds < _MIN_INTERVAL:
            raise SpecError("interval ต้องอย่างน้อย 1 นาที")
        return ("interval", str(seconds))

    if text.startswith("daily "):
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", text[6:].strip())
        if not m:
            raise SpecError("รูปแบบเวลาไม่ถูกต้อง เช่น 'daily 09:00'")
        hh, mm = int(m.group(1)), int(m.group(2))
        if not (0 <= hh < 24 and 0 <= mm < 60):
            raise SpecError("เวลาไม่ถูกต้อง (00:00–23:59)")
        return ("daily", f"{hh:02d}:{mm:02d}")

    if text.startswith("cron "):
        cron = text[5:].strip()
        if len(cron.split()) != 5:
            raise SpecError("cron ต้องมี 5 ช่อง เช่น 'cron 0 9 * * *'")
        return ("cron", cron)

    raise SpecError(
        "ไม่รู้จักรูปแบบ — ใช้: 'every 30m' | 'daily 09:00' | 'cron 0 9 * * *'"
    )


def describe(trigger_type: str, trigger_arg: str) -> str:
    """Human-readable one-liner for a stored trigger."""
    if trigger_type == "interval":
        secs = int(trigger_arg)
        if secs % 86400 == 0:
            return f"ทุก {secs // 86400} วัน"
        if secs % 3600 == 0:
            return f"ทุก {secs // 3600} ชม."
        return f"ทุก {secs // 60} นาที"
    if trigger_type == "daily":
        return f"ทุกวัน {trigger_arg}"
    if trigger_type == "cron":
        return f"cron: {trigger_arg}"
    return f"{trigger_type} {trigger_arg}"
