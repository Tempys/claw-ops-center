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


def test_state_has_per_source_raw_signal_fields():
    from news.state import State
    s: State = {
        "telegram_offset_id": 0,
        "telegram_raw_signals": [],
        "telegram_seen_hashes": [],
        "email_last_checked": 0.0,
        "email_raw_signals": [],
        "email_seen_hashes": [],
        "filtered_signals": [],
    }
    assert s["telegram_raw_signals"] == []
    assert s["email_raw_signals"] == []
    assert s["telegram_seen_hashes"] == []
    assert s["email_seen_hashes"] == []


def test_filtered_signals_reducer_merges_two_lists():
    import operator
    from typing import get_type_hints, get_args
    import news.state as state_module

    hints = get_type_hints(state_module.State, include_extras=True)
    annotation = hints["filtered_signals"]
    # Annotated[list[Signal], operator.add] — second arg is the reducer
    reducer = get_args(annotation)[1]
    assert reducer([{"title": "a"}], [{"title": "b"}]) == [{"title": "a"}, {"title": "b"}]


def test_seen_hashes_reducer_deduplicates():
    import news.state as state_module
    from typing import get_type_hints, get_args

    hints = get_type_hints(state_module.State, include_extras=True)
    annotation = hints["telegram_seen_hashes"]
    reducer = get_args(annotation)[1]
    assert sorted(reducer(["a", "b"], ["b", "c"])) == ["a", "b", "c"]
