# news/nodes/email_analyzer.py
from news.nodes.analyzer import _classify_batch
from news.prompts.email_classify import SYSTEM as _EMAIL_SYSTEM
from news.state import State

_BATCH_SIZE = 5


async def email_analyze_node(state: State) -> dict:
    signals = state["email_raw_signals"][:_BATCH_SIZE]
    classified = await _classify_batch(signals, _EMAIL_SYSTEM)
    filtered = [s for s in classified if s["classification"] not in {"other", "error"}]
    return {"filtered_signals": filtered}
