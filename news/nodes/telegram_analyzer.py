# news/nodes/telegram_analyzer.py
from news.nodes.analyzer import _classify_batch
from news.state import Signal, State

_TELEGRAM_SYSTEM = (
    "You are a signal classifier for a curated ML/AI Telegram channel. "
    "Posts are short — often just a title, a URL, or a few sentences. "
    "The channel is tech-focused so be aggressive: classify borderline posts rather than defaulting to 'other'. "
    "Return ONLY a JSON array — no prose, no markdown. "
    "Each element: {\"index\": <int>, \"classification\": <category>}. "
    "Valid categories: ai_agent_framework, llm_finetuning, skill_plugin_builder, "
    "code_generation, dev_productivity, prompt_engineering, other."
)

_BATCH_SIZE = 10


async def telegram_analyze_node(state: State) -> dict:
    signals = state["telegram_raw_signals"][:_BATCH_SIZE]
    classified: list[Signal] = []
    for i in range(0, len(signals), 5):  # 5 signals per LLM call to stay within token budget
        classified.extend(await _classify_batch(signals[i : i + 5], _TELEGRAM_SYSTEM))
    filtered = [s for s in classified if s["classification"] not in {"other", "error"}]
    return {"filtered_signals": filtered}
