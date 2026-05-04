# news/nodes/email_analyzer.py
from news.nodes.analyzer import _classify_batch
from news.state import State

_EMAIL_SYSTEM = (
    "You are a signal classifier for AI/dev-tool newsletters and email digests. "
    "Emails are long-form. Focus on the subject line and first paragraph. "
    "Aggressively discard: promotional emails, subscription confirmations, HR/admin messages, "
    "general tech news not specific to AI or developer tooling. "
    "Return ONLY a JSON array — no prose, no markdown. "
    "Each element: {\"index\": <int>, \"classification\": <category>}. "
    "Valid categories: ai_agent_framework, llm_finetuning, skill_plugin_builder, "
    "code_generation, dev_productivity, prompt_engineering, other."
)

_BATCH_SIZE = 5


async def email_analyze_node(state: State) -> dict:
    signals = state["email_raw_signals"][:_BATCH_SIZE]
    classified = await _classify_batch(signals, _EMAIL_SYSTEM)
    filtered = [s for s in classified if s["classification"] not in {"other", "error"}]
    return {"filtered_signals": filtered}
