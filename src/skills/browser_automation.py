"""Browser automation skill — headless page render + screenshot via Playwright.

Playwright is heavy, so the browser is launched only when this skill runs, and
the import is done inside the handler so the rest of the app starts without it.
Requires `playwright install chromium` (see docs/HOSTINGER_DEPLOY.md).
"""
from __future__ import annotations

import re

from src.skills.base import Skill, SkillResult

_URL_RE = re.compile(r"https?://[^\s]+")


async def _handle(text: str) -> SkillResult:
    match = _URL_RE.search(text)
    if not match:
        return SkillResult(ok=False, text="No URL found to open in the browser.")
    url = match.group(0)
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return SkillResult(
            ok=False,
            text="Playwright is not installed. Run: pip install playwright && playwright install chromium",
        )

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page_title = await page.title()
            await browser.close()
    except Exception as exc:  # Playwright raises a broad set of errors
        return SkillResult(ok=False, text=f"Browser automation failed for {url}: {exc}")

    return SkillResult(
        ok=True,
        text=f"Opened {url} — page title: {page_title!r}",
        meta={"url": url, "title": page_title},
    )


browser_automation = Skill(
    name="browser_automation",
    description="Open a page headlessly and read its rendered title (Playwright).",
    handler=_handle,
)
