"""FastAPI app — health, usage, and a stateless /agent endpoint.

The same Hermes engine that powers the Telegram bot is exposed over HTTP so the
future dashboard / API-sales tier can reuse it. No auth yet — front it with a
reverse proxy + API key before exposing publicly (see docs/API.md).
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from src import __version__
from src.agent.hermes import handle_message
from src.config import get_settings
from src.llm.openrouter import llm_client

app = FastAPI(title="Big-D-Agent", version=__version__)


@app.get("/health")
async def health() -> dict:
    settings = get_settings()
    return {
        "status": "ok",
        "version": __version__,
        "environment": settings.environment,
        "telegram_configured": settings.telegram_configured,
        "openrouter_configured": settings.openrouter_configured,
    }


@app.get("/usage")
async def usage() -> dict:
    u = llm_client.usage
    return {
        "requests": u.requests,
        "prompt_tokens": u.prompt_tokens,
        "completion_tokens": u.completion_tokens,
        "total_tokens": u.total_tokens,
    }


class AgentRequest(BaseModel):
    message: str


class AgentResponse(BaseModel):
    reply: str
    intent: str
    skill: str | None = None


@app.post("/agent", response_model=AgentResponse)
async def agent(req: AgentRequest) -> AgentResponse:
    result = await handle_message(req.message)
    return AgentResponse(reply=result.text, intent=result.intent.value, skill=result.skill)
