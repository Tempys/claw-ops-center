import openai
import logging

import news.config as config
from news.state import Signal, State

log = logging.getLogger(__name__)

_client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)

_SYSTEM = (
    "You are an intelligence analyst. Given signals collected from Telegram channels and email, "
    "produce a concise digest. Lead with urgent items, follow with informational, omit noise. "
    "Be factual and brief."
)


def _format_signals(signals: list[Signal]) -> str:
    lines = ["Signals collected this run:\n"]
    for i, s in enumerate(signals, 1):
        lines.append(f"{i}. [{s['source'].upper()}] {s['title']}\n   {s['summary']}\n")
    return "\n".join(lines)


async def analyze_and_classify_node(state: State) -> dict:
    signals = state["signals"]
    parts = []
    for i in range(0, len(signals), 5):
        batch = signals[i : i + 5]
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": _format_signals(batch)},
            ],
        )
        parts.append(response.choices[0].message.content)
    return {"analysis": "\n\n".join(parts)}
