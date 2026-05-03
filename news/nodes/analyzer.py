import anthropic
import logging

import news.config as config
from news.state import Signal, State

log = logging.getLogger(__name__)

_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

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
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _format_signals(state["signals"])}],
    )
    return {"analysis": response.content[0].text}
