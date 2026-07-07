"""Rough USD cost estimation per model, for the cost guard.

These are approximate list prices (USD per 1K tokens) used only to keep a daily
spend estimate — not billing-grade. Unknown models fall back to a safe default
so the guard errs toward caution. Update as OpenRouter pricing changes.
"""
from __future__ import annotations

# (prompt_per_1k, completion_per_1k) in USD. Matched by substring, first hit.
_PRICES: list[tuple[str, tuple[float, float]]] = [
    ("gpt-4o-mini", (0.00015, 0.00060)),
    ("gpt-4o", (0.0025, 0.010)),
    ("claude-3.5-sonnet", (0.003, 0.015)),
    ("claude-3-haiku", (0.00025, 0.00125)),
    ("deepseek", (0.00014, 0.00028)),
    ("gemini", (0.00010, 0.00040)),
]
_DEFAULT = (0.002, 0.006)


def estimate_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    """Estimate the USD cost of one completion."""
    pin, pout = _DEFAULT
    lowered = model.lower()
    for needle, (a, b) in _PRICES:
        if needle in lowered:
            pin, pout = a, b
            break
    return (prompt_tokens / 1000) * pin + (completion_tokens / 1000) * pout
