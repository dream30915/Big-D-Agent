"""Skill registry.

Each skill is a small async callable with a name + description. The agent picks
one by intent; new skills only need to be added to SKILLS to become available.
"""
from __future__ import annotations

from src.skills.base import Skill
from src.skills.content_creation import content_creation
from src.skills.customer_service import customer_service
from src.skills.data_analysis import data_analysis
from src.skills.web_scraping import web_scraping

# browser_automation is imported lazily inside its module note (Playwright is
# heavy); it is registered here but only spins up a browser when invoked.
from src.skills.browser_automation import browser_automation

SKILLS: dict[str, Skill] = {
    s.name: s
    for s in (
        web_scraping,
        browser_automation,
        content_creation,
        customer_service,
        data_analysis,
    )
}

__all__ = ["SKILLS", "Skill"]
