# news/nodes/telegram_dedup.py
import hashlib

from news.state import Signal, State


def _signal_hash(signal: Signal) -> str:
    key = f"{signal['title']}:{signal['summary'][:200]}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


async def telegram_dedup_node(state: State) -> dict:
    seen = set(state.get("telegram_seen_hashes", []))
    new_hashes: list[str] = []
    deduped: list[Signal] = []

    for signal in state["telegram_raw_signals"]:
        if signal["classification"] == "error":
            deduped.append(signal)
            continue
        h = _signal_hash(signal)
        if h not in seen:
            deduped.append(signal)
            seen.add(h)
            new_hashes.append(h)

    return {
        "telegram_raw_signals": deduped,
        "telegram_seen_hashes": new_hashes,
    }
