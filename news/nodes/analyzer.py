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
        lines.append(
            f"{i}. [{s['source'].upper()}][{s['classification']}] {s['title']}\n   {s['summary']}\n"
        )
    return "\n".join(lines)


async def _classify_batch(signals: list[Signal], system_prompt: str) -> list[Signal]:
    non_error = [s for s in signals if s["classification"] != "error"]
    if not non_error:
        return signals

    try:
        response = await _client.responses.create(
            model="gpt-4o-mini",
            max_output_tokens=512,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": _format_signals(non_error)},
            ],
        )
        items = json.loads(response.output_text)
        index_map = {
            item["index"]: item["classification"]
            for item in items
            if isinstance(item.get("index"), int)
        }
    except Exception:
        log.warning("Classify pass failed, falling back to 'other'", exc_info=True)
        index_map = {}

    classified_non_error: list[Signal] = []
    for i, signal in enumerate(non_error, 1):
        raw_cls = index_map.get(i, "other")
        cls = raw_cls if raw_cls in _CLASSIFIABLE else "other"
        classified_non_error.append({**signal, "classification": cls})

    ne_iter = iter(classified_non_error)
    return [next(ne_iter) if s["classification"] != "error" else s for s in signals]
