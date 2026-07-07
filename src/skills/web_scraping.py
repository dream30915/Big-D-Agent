"""Web scraping skill — fetch a URL and summarise its readable text.

Real implementation: pulls the first URL out of the message with httpx, parses
it with BeautifulSoup, strips script/style, and returns a trimmed text preview.
The caller (Hermes) can then hand that text to the LLM for summarisation.
"""
from __future__ import annotations

import re

import httpx
from bs4 import BeautifulSoup

from src.skills.base import Skill, SkillResult

_URL_RE = re.compile(r"https?://[^\s]+")
_MAX_CHARS = 4000


async def _handle(text: str) -> SkillResult:
    match = _URL_RE.search(text)
    if not match:
        return SkillResult(ok=False, text="No URL found in the message to scrape.")
    url = match.group(0)
    try:
        async with httpx.AsyncClient(
            timeout=20.0, follow_redirects=True, headers={"User-Agent": "Big-D-Agent/0.1"}
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            html = resp.text
    except httpx.HTTPError as exc:
        return SkillResult(ok=False, text=f"Failed to fetch {url}: {exc}")

    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    title = (soup.title.string or "").strip() if soup.title else ""
    body = " ".join(soup.get_text(separator=" ").split())
    preview = body[:_MAX_CHARS]
    return SkillResult(
        ok=True,
        text=preview,
        meta={"url": url, "title": title, "chars": len(body)},
    )


web_scraping = Skill(
    name="web_scraping",
    description="Fetch a URL and extract its readable text (BeautifulSoup).",
    handler=_handle,
)
