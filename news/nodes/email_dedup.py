# news/nodes/email_dedup.py
import hashlib

from news.state import Signal, State


def _signal_hash(signal: Signal) -> str:
    return hashlib.sha256(signal["url"].encode()).hexdigest()[:16]


async def email_dedup_node(state: State) -> dict:
    seen = set(state.get("email_seen_hashes", []))
    new_hashes: list[str] = []
    deduped: list[Signal] = []

    for signal in state.get("email_raw_signals", []):
        h = _signal_hash(signal)
        if h not in seen:
            deduped.append(signal)
            seen.add(h)
            new_hashes.append(h)

    return {
        "email_raw_signals": deduped,
        "email_seen_hashes": new_hashes,
    }
