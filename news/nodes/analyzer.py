import json
import logging
from typing import get_args

import openai

import news.config as config
from news.state import CLASSIFICATION, Signal, State

log = logging.getLogger(__name__)

_client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)

_VALID_CLASSIFICATIONS = set(get_args(CLASSIFICATION))

_CLASSIFY_SYSTEM = (
    "You are a signal classifier. Given a numbered list of signals, return ONLY a JSON array — "
    "no prose, no markdown. Each element: {\"index\": <int>, \"classification\": <category>}. "
    "Valid categories: ai_agent_framework, llm_finetuning, skill_plugin_builder, code_generation, "
    "dev_productivity, prompt_engineering, other, error."
)

_DIGEST_SYSTEM = (
    "You are an intelligence analyst. Given classified signals from Telegram channels and email, "
    "produce a concise digest. Lead with dev-tool signals "
    "(ai_agent_framework, llm_finetuning, skill_plugin_builder, code_generation, dev_productivity, "
    "prompt_engineering), then other signals. Omit noise. Be factual and brief."
)


def _format_signals(signals: list[Signal]) -> str:
    lines = ["Signals collected this run:\n"]
    for i, s in enumerate(signals, 1):
        lines.append(
            f"{i}. [{s['source'].upper()}][{s['classification']}] {s['title']}\n   {s['summary']}\n"
        )
    return "\n".join(lines)


async def _classify_batch(signals: list[Signal]) -> list[Signal]:
    if all(s["classification"] == "error" for s in signals):
        return signals

    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": _format_signals(signals)},
            ],
        )
        items = json.loads(response.choices[0].message.content)
        index_map = {
            item["index"]: item["classification"]
            for item in items
            if isinstance(item.get("index"), int)
        }
    except Exception:
        log.warning("Classify pass failed, falling back to 'other'", exc_info=True)
        index_map = {}

    result = []
    for i, signal in enumerate(signals, 1):
        if signal["classification"] == "error":
            result.append(signal)
            continue
        raw_cls = index_map.get(i, "other")
        cls = raw_cls if raw_cls in _VALID_CLASSIFICATIONS else "other"
        result.append({**signal, "classification": cls})
    return result


async def analyze_and_classify_node(state: State) -> dict:
    signals = state["signals"]
    parts = []

    for i in range(0, len(signals), 5):
        batch = await _classify_batch(signals[i : i + 5])
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _DIGEST_SYSTEM},
                {"role": "user", "content": _format_signals(batch)},
            ],
        )
        parts.append(response.choices[0].message.content)

    return {"analysis": "\n\n".join(parts)}
