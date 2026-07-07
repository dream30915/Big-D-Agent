"""Lightweight ethics / compliance gate.

This is intentionally simple and transparent: a keyword screen that flags
requests the agent should refuse or escalate. It is NOT a substitute for the
underlying model's own safety, but gives us a local, auditable checkpoint that
the plan calls for (feature: "Ethics & Compliance").
"""
from __future__ import annotations

from dataclasses import dataclass

# Categories we refuse outright. Kept short and readable on purpose.
_BLOCKED_PATTERNS: dict[str, tuple[str, ...]] = {
    "malware": ("write malware", "ransomware", "keylogger", "build a botnet"),
    "fraud": ("steal credit card", "carding", "fake passport", "launder money"),
    "harm": ("how to make a bomb", "build a weapon", "synthesize a nerve agent"),
}


@dataclass(frozen=True)
class EthicsVerdict:
    allowed: bool
    category: str | None = None
    reason: str | None = None


def check(text: str) -> EthicsVerdict:
    """Return an allow/deny verdict for a user request."""
    lowered = text.lower()
    for category, patterns in _BLOCKED_PATTERNS.items():
        for pattern in patterns:
            if pattern in lowered:
                return EthicsVerdict(
                    allowed=False,
                    category=category,
                    reason=f"request matches blocked category '{category}'",
                )
    return EthicsVerdict(allowed=True)
