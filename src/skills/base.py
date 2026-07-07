"""Skill protocol + result type shared by every skill."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class SkillResult:
    ok: bool
    text: str
    meta: dict | None = None


# A skill handler takes the raw user text and returns a SkillResult.
SkillHandler = Callable[[str], Awaitable[SkillResult]]


@dataclass
class Skill:
    name: str
    description: str
    handler: SkillHandler

    async def run(self, text: str) -> SkillResult:
        return await self.handler(text)
