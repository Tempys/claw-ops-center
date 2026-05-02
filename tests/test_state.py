import operator
from typing import get_type_hints


def test_signal_fields():
    from openclaw.state import Signal
    s: Signal = {
        "title": "BTC surge",
        "classification": "urgent",
        "summary": "BTC up 15% in 1h",
        "source": "telegram",
    }
    assert s["title"] == "BTC surge"
    assert s["classification"] == "urgent"
    assert s["summary"] == "BTC up 15% in 1h"
    assert s["source"] == "telegram"


def test_state_has_required_fields():
    from openclaw.state import State
    hints = get_type_hints(State, include_extras=True)
    assert "telegram_offset_id" in hints
    assert "email_last_checked" in hints
    assert "signals" in hints
    assert "analysis" in hints


def test_signals_reducer_merges_lists():
    # operator.add is the fan-in reducer LangGraph uses for Annotated[list, operator.add]
    a = [{"title": "A", "classification": "informational", "summary": "a", "source": "telegram"}]
    b = [{"title": "B", "classification": "informational", "summary": "b", "source": "email"}]
    merged = operator.add(a, b)
    assert len(merged) == 2
    assert merged[0]["source"] == "telegram"
    assert merged[1]["source"] == "email"
