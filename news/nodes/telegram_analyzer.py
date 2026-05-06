# news/nodes/telegram_analyzer.py
import asyncio
import logging
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel

import news.config as config
from news.prompts.telegram_classify import SYSTEM as _SYSTEM
from news.state import EnrichedSignal, Signal, State

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
_MODEL = "gpt-4o-mini"

_CATEGORIES = [
    "ai_agent_framework",
    "llm_finetuning",
    "skill_plugin_builder",
    "code_generation",
    "dev_productivity",
    "prompt_engineering",
    "other",
]


class ClassificationResult(BaseModel):
    classification: Literal[
        "ai_agent_framework",
        "llm_finetuning",
        "skill_plugin_builder",
        "code_generation",
        "dev_productivity",
        "prompt_engineering",
        "other",
    ]
    description: str
    reason: str


async def _classify_one(signal: EnrichedSignal) -> Signal:
    text = signal["summary"] or signal["title"]
    github_block = (
        f"\n\nGitHub README excerpt:\n{signal['readme_excerpt']}"
        if signal["readme_excerpt"]
        else ""
    )

    try:
        resp = await _client.responses.parse(
            model=_MODEL,
            max_output_tokens=256,
            input=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Post:\n{text}{github_block}"},
            ],
            text_format=ClassificationResult,
        )
        result = resp.output_parsed
        if result is None:
            raise ValueError("Structured output parsing returned None")
        enriched_summary = f"{result.description} — {result.reason}".strip(" —")
        return Signal(
            title=signal["title"],
            classification=result.classification,
            summary=enriched_summary,
            source=signal["source"],
        )
    except Exception:
        log.warning("Classification failed: %s", signal["title"][:60], exc_info=True)
        return Signal(
            title=signal["title"],
            classification="other",
            summary=signal["summary"],
            source=signal["source"],
        )


async def telegram_analyze_node(state: State) -> dict:
    signals = state["telegram_enriched_signals"][:10]
    classified = await asyncio.gather(*(_classify_one(s) for s in signals))
    filtered = [s for s in classified if s["classification"] not in {"other", "error"}]
    return {"filtered_signals": list(filtered)}
