# news/nodes/email_analyzer.py
from news.nodes.analyzer import _classify_batch
from news.prompts import load_prompt
from news.state import EmailState

_EMAIL_SYSTEM = load_prompt("email_classify")

_BATCH_SIZE = 5


async def email_analyze_node(state: EmailState) -> dict:
    signals = state.get("email_raw_signals", [])[:_BATCH_SIZE]
    classified = await _classify_batch(signals, _EMAIL_SYSTEM)
    return {"filtered_signals": classified}
