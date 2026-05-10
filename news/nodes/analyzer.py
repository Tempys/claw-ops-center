import json
import logging
from typing import get_args

import openai

import news.config as config
from news.state import CLASSIFICATION, Signal

log = logging.getLogger(__name__)

_client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)

_VALID_CLASSIFICATIONS = set(get_args(CLASSIFICATION))
_CLASSIFIABLE = _VALID_CLASSIFICATIONS - {"error"}


def _format_signals(signals: list[Signal]) -> str:
    lines = ["Signals collected this run:\n"]
    for i, s in enumerate(signals, 1):
        lines.append(f"{i}. {s['url']}\n")
    return "\n".join(lines)


async def _classify_batch(signals: list[Signal], system_prompt: str) -> list[Signal]:
    if not signals:
        return signals

    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=512,
            messages=[
                {"role": "system", "content": system_prompt},
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

    result: list[Signal] = []
    for i, signal in enumerate(signals, 1):
        raw_cls = index_map.get(i, "other")
        cls = raw_cls if raw_cls in _CLASSIFIABLE else "other"
        result.append({**signal, "classification": cls})  # type: ignore[misc]
    return result
