import operator
from typing import get_type_hints


def test_classification_literal_contains_expected_values():
    from typing import get_args
    from news.state import CLASSIFICATION
    values = set(get_args(CLASSIFICATION))
    assert values == {
        "ai_agent_framework",
        "llm_finetuning",
        "skill_plugin_builder",
        "code_generation",
        "dev_productivity",
        "prompt_engineering",
        "other",
        "error",
    }


def test_signal_classification_accepts_new_values():
    from news.state import Signal
    s: Signal = {
        "title": "LangGraph 2.0 released",
        "classification": "ai_agent_framework",
        "summary": "Major update to LangGraph",
        "source": "telegram",
    }
    assert s["classification"] == "ai_agent_framework"


def test_signal_fields():
    from news.state import Signal
    s: Signal = {
        "title": "BTC surge",
        "classification": "other",
        "summary": "BTC up 15% in 1h",
        "source": "telegram",
    }
    assert s["title"] == "BTC surge"
    assert s["classification"] == "other"
    assert s["summary"] == "BTC up 15% in 1h"
    assert s["source"] == "telegram"


def test_state_has_required_fields():
    from news.state import State
    hints = get_type_hints(State, include_extras=True)
    assert "telegram_offset_id" in hints
    assert "email_last_checked" in hints
    assert "signals" in hints
    assert "analysis" in hints


def test_signals_reducer_merges_lists():
    a = [{"title": "A", "classification": "other", "summary": "a", "source": "telegram"}]
    b = [{"title": "B", "classification": "other", "summary": "b", "source": "email"}]
    merged = operator.add(a, b)
    assert len(merged) == 2
    assert merged[0]["source"] == "telegram"
    assert merged[1]["source"] == "email"
