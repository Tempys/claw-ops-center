# news/nodes/telegram_analyzer.py
import asyncio
import logging
import re
from typing import Literal, get_args

from openai import AsyncOpenAI
from pydantic import BaseModel

import news.config as config
from news.prompts import load_prompt
from news.state import ExtractNodeOutput, State

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


async def _classify_one(signal: ExtractNodeOutput) -> ClassificationResult:
    readme_text = _clean_text(signal["readme"])
    content = f"GitHub: {signal['github_link']}\n\nREADME:\n{readme_text}"

    resp = await _client.beta.chat.completions.parse(
        model=_MODEL,
        max_tokens=256,
        messages=[
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": content},
        ],
        response_format=ClassificationResult,
    )
    result = resp.choices[0].message.parsed
    if result is None:
        raise ValueError("Structured output parsing returned None")
    return result


async def telegram_analyze_node(state: State) -> dict:
    signals = state["telegram_extracted_signals"][:_MAX_SIGNALS]
    results = await asyncio.gather(*(_classify_one(s) for s in signals), return_exceptions=True)
    filtered = [
        sig for sig, result in zip(signals, results)
        if not isinstance(result, BaseException) and result.classification not in {"other", "error"}
    ]
    return {"filtered_signals": filtered}
