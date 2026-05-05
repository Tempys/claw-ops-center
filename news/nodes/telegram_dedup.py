# news/nodes/telegram_dedup.py
from news.state import Signal, State


async def telegram_dedup_node(state: State) -> dict:
    seen: set[tuple] = set()
    deduped = [
        s for s in state["telegram_raw_signals"]
        if (k := (s["title"], s["summary"])) not in seen and not seen.add(k)
    ]
    return {"telegram_raw_signals": deduped}
