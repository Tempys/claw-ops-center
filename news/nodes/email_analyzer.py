# news/nodes/email_analyzer.py
from news.nodes.analyzer import _classify_batch
from news.prompts import load_prompt
from news.state import State

_EMAIL_SYSTEM = load_prompt("email_classify")

_BATCH_SIZE = 5


async def email_analyze_node(state: State) -> dict:
    signals = state["email_raw_signals"][:_BATCH_SIZE]
    classified = await _classify_batch(signals, _EMAIL_SYSTEM)
    filtered = [s for s in classified if s["classification"] not in {"other", "error"}]
    return {"filtered_signals": filtered}
