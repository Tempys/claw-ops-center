# news/nodes/telegram_analyzer.py
import asyncio
import logging
import re
from typing import Literal, get_args

from openai import AsyncOpenAI
from pydantic import BaseModel

import news.config as config
from news.prompts import load_prompt
from news.state import EnrichedSignal, State

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
_MODEL = "gpt-4o-mini"
_MAX_SIGNALS = 10


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
    @property
    def summary(self) -> str:
        return f"{self.description} — {self.reason}".removesuffix(" —")


_SYSTEM = load_prompt(
    "telegram_classify",
    categories=", ".join(list(get_args(ClassificationResult.model_fields["classification"].annotation))),
)

_STARS_TREND_RE = re.compile(r"Stars trend:.*", re.DOTALL | re.IGNORECASE)


def _clean_text(text: str) -> str:
    return _STARS_TREND_RE.sub("", text).strip()


async def _classify_one(signal: EnrichedSignal) -> ClassificationResult:
    text = _clean_text(signal["summary"] or signal["title"])
    github_block = (
        f"\n\nGitHub README excerpt:\n{signal['readme_excerpt']}"
        if signal["readme_excerpt"]
        else ""
    )

    resp = await _client.beta.chat.completions.parse(
        model=_MODEL,
        max_tokens=256,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": f"Post:\n{text}{github_block}"},
        ],
        response_format=ClassificationResult,
    )
    result = resp.choices[0].message.parsed
    if result is None:
        raise ValueError("Structured output parsing returned None")
    return result


async def telegram_analyze_node(state: State) -> dict:
    signals = state["telegram_enriched_signals"][:_MAX_SIGNALS]
    results = await asyncio.gather(*(_classify_one(s) for s in signals), return_exceptions=True)
    filtered = [
        s for s in results
        if not isinstance(s, BaseException) and s.classification not in {"other", "error"}
    ]
    return {"filtered_signals": list(filtered)}
