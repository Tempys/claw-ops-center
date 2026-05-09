# news/nodes/telegram_dedup.py
import hashlib

from news.state import TelegramPipelineState


def _signal_hash(signal: dict) -> str:
    return hashlib.sha256(signal["url"].encode()).hexdigest()


async def telegram_dedup_node(state: TelegramPipelineState) -> dict:
    seen = set()
    deduped = []

    for s in state.get("telegram_raw_signals", []):
        h = _signal_hash(s)
        if h not in seen:
            deduped.append(s)
            seen.add(h)

    return {
        "telegram_raw_signals": deduped,
    }
