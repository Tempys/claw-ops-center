# Per-Message Classify and Send Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the batch-digest pipeline with a per-message flow that classifies each signal, forwards only dev-tool ones as raw text to Telegram, and silently drops everything else.

**Architecture:** `telegram_collector` stays unchanged. `analyze_and_classify_node` is replaced by `classify_and_filter_node` which classifies signals in batches of 5 and returns only dev-tool ones in `State.filtered_signals`. `sender_node` iterates `filtered_signals` and sends each `summary` as a separate Telegram message. `State.analysis` is removed.

**Tech Stack:** Python 3.12+, openai>=2.0.0, langgraph, python-telegram-bot, pytest-asyncio (asyncio_mode=auto)

---

## File Map

| File | Change |
|------|--------|
| `news/state.py` | Remove `analysis: str`; add `filtered_signals: list[Signal]` |
| `tests/test_state.py` | Update field assertions |
| `news/nodes/analyzer.py` | Remove `analyze_and_classify_node` and `_DIGEST_SYSTEM`; add `classify_and_filter_node` |
| `tests/test_analyzer.py` | Replace node-level tests; keep `_classify_batch` tests unchanged |
| `news/nodes/sender.py` | Iterate `filtered_signals`, send each `summary` |
| `tests/test_sender.py` | Rewrite for per-message sending |
| `news/graph.py` | Swap `analyze_and_classify` → `classify_and_filter` |
| `news/runner.py` | Replace `analysis: ""` with `filtered_signals: []` in `_INITIAL_STATE` |
| `tests/test_graph.py` | Update node name and integration state |

---

## Task 1: Update State — remove analysis, add filtered_signals

**Files:**
- Modify: `news/state.py`
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write the failing test**

In `tests/test_state.py`, replace `test_state_has_required_fields` with:

```python
def test_state_has_required_fields():
    from news.state import State
    hints = get_type_hints(State, include_extras=True)
    assert "telegram_offset_id" in hints
    assert "email_last_checked" in hints
    assert "signals" in hints
    assert "filtered_signals" in hints
    assert "analysis" not in hints
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_state.py::test_state_has_required_fields -v
```

Expected: FAIL — `AssertionError: assert 'analysis' not in hints`

- [ ] **Step 3: Update news/state.py**

Replace the entire file with:

```python
import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict


CLASSIFICATION = Literal[
    "ai_agent_framework",
    "llm_finetuning",
    "skill_plugin_builder",
    "code_generation",
    "dev_productivity",
    "prompt_engineering",
    "other",
    "error",
]


class Signal(TypedDict):
    title: str
    classification: CLASSIFICATION
    summary: str
    source: str


class State(TypedDict):
    telegram_offset_id: int
    email_last_checked: float
    signals: Annotated[list[Signal], operator.add]
    filtered_signals: list[Signal]
```

- [ ] **Step 4: Run all state tests**

```bash
venv/bin/pytest tests/test_state.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add news/state.py tests/test_state.py
git commit -m "feat: replace State.analysis with State.filtered_signals"
```

---

## Task 2: Rewrite analyzer — classify_and_filter_node

**Files:**
- Modify: `news/nodes/analyzer.py`
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing tests for classify_and_filter_node**

In `tests/test_analyzer.py`, replace the three node-level tests that reference `analyze_and_classify_node` (`test_returns_analysis_text`, `test_error_signals_bypass_classify_pass`, `test_digest_prompt_includes_classification_labels`) with these three new tests. Keep all five `_classify_batch` tests unchanged.

The new STATE fixture must also drop `"analysis"`:

```python
import json
from unittest.mock import AsyncMock, MagicMock, patch


def _make_openai_response(text: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    return response


STATE = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [
        {"title": "LangGraph 2.0 drops", "classification": "other", "summary": "Major LangGraph release with new features", "source": "telegram"},
        {"title": "BTC price update", "classification": "other", "summary": "BTC up 5%", "source": "telegram"},
    ],
    "filtered_signals": [],
}

STATE_WITH_ERROR = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [
        {"title": "Collector failed", "classification": "error", "summary": "connection refused", "source": "telegram"},
        {"title": "AutoGen workshop", "classification": "other", "summary": "New AutoGen tutorial repo", "source": "telegram"},
    ],
    "filtered_signals": [],
}


async def test_classify_and_filter_node_returns_dev_tool_signals():
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import classify_and_filter_node
        result = await classify_and_filter_node(STATE)

    assert "filtered_signals" in result
    assert len(result["filtered_signals"]) == 1
    assert result["filtered_signals"][0]["classification"] == "ai_agent_framework"
    assert result["filtered_signals"][0]["title"] == "LangGraph 2.0 drops"


async def test_classify_and_filter_node_drops_other_and_error():
    classify_json = json.dumps([
        {"index": 1, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import classify_and_filter_node
        result = await classify_and_filter_node(STATE_WITH_ERROR)

    assert result["filtered_signals"] == []


async def test_classify_and_filter_node_returns_empty_when_all_other():
    classify_json = json.dumps([
        {"index": 1, "classification": "other"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import classify_and_filter_node
        result = await classify_and_filter_node(STATE)

    assert result["filtered_signals"] == []


# ── _classify_batch tests (unchanged) ──────────────────────────────────────

async def test_classify_pass_updates_signal_classification():
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "LangGraph 2.0 drops", "classification": "other", "summary": "Major LangGraph release", "source": "telegram"},
            {"title": "BTC price update", "classification": "other", "summary": "BTC up 5%", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    assert result[0]["classification"] == "ai_agent_framework"
    assert result[1]["classification"] == "other"


async def test_classify_pass_falls_back_to_other_on_invalid_json():
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("not valid json {{{{")
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "LangGraph 2.0 drops", "classification": "other", "summary": "Major LangGraph release", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    assert result[0]["classification"] == "other"


async def test_classify_pass_coerces_unknown_category_to_other():
    classify_json = json.dumps([{"index": 1, "classification": "definitely_not_valid"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "Some signal", "classification": "other", "summary": "content", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    assert result[0]["classification"] == "other"


async def test_error_only_batch_skips_classify_call():
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("Digest text")
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "Collector failed", "classification": "error", "summary": "err", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    mock_client.chat.completions.create.assert_not_called()
    assert result[0]["classification"] == "error"


async def test_classify_pass_coerces_error_classification_to_other():
    classify_json = json.dumps([{"index": 1, "classification": "error"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "Some signal", "classification": "other", "summary": "content", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    assert result[0]["classification"] == "other"
```

- [ ] **Step 2: Run to verify the three new tests fail**

```bash
venv/bin/pytest tests/test_analyzer.py::test_classify_and_filter_node_returns_dev_tool_signals tests/test_analyzer.py::test_classify_and_filter_node_drops_other_and_error tests/test_analyzer.py::test_classify_and_filter_node_returns_empty_when_all_other -v
```

Expected: FAIL — `ImportError: cannot import name 'classify_and_filter_node'`

- [ ] **Step 3: Rewrite news/nodes/analyzer.py**

Replace the entire file with:

```python
import json
import logging
from typing import get_args

import openai

import news.config as config
from news.state import CLASSIFICATION, Signal, State

log = logging.getLogger(__name__)

_client = openai.AsyncOpenAI(api_key=config.OPENAI_API_KEY)

_VALID_CLASSIFICATIONS = set(get_args(CLASSIFICATION))
_CLASSIFIABLE = _VALID_CLASSIFICATIONS - {"error"}

_CLASSIFY_SYSTEM = (
    "You are a signal classifier. Given a numbered list of signals, return ONLY a JSON array — "
    "no prose, no markdown. Each element: {\"index\": <int>, \"classification\": <category>}. "
    "Valid categories: ai_agent_framework, llm_finetuning, skill_plugin_builder, code_generation, "
    "dev_productivity, prompt_engineering, other."
)


def _format_signals(signals: list[Signal]) -> str:
    lines = ["Signals collected this run:\n"]
    for i, s in enumerate(signals, 1):
        lines.append(
            f"{i}. [{s['source'].upper()}][{s['classification']}] {s['title']}\n   {s['summary']}\n"
        )
    return "\n".join(lines)


async def _classify_batch(signals: list[Signal]) -> list[Signal]:
    non_error = [s for s in signals if s["classification"] != "error"]
    if not non_error:
        return signals

    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=512,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": _format_signals(non_error)},
            ],
        )
        items = json.loads(response.choices[0].message.content)
        index_map = {
            item["index"]: item["classification"]
            for item in items
            if isinstance(item.get("index"), int)
        }
    except Exception:
        log.warning("Classify pass failed, falling back to 'other'", exc_info=True)
        index_map = {}

    classified_non_error: list[Signal] = []
    for i, signal in enumerate(non_error, 1):
        raw_cls = index_map.get(i, "other")
        cls = raw_cls if raw_cls in _CLASSIFIABLE else "other"
        classified_non_error.append({**signal, "classification": cls})

    ne_iter = iter(classified_non_error)
    return [next(ne_iter) if s["classification"] != "error" else s for s in signals]


async def classify_and_filter_node(state: State) -> dict:
    signals = state["signals"]
    classified: list[Signal] = []
    for i in range(0, len(signals), 5):
        classified.extend(await _classify_batch(signals[i : i + 5]))
    dev_tool = [s for s in classified if s["classification"] not in {"other", "error"}]
    return {"filtered_signals": dev_tool}
```

- [ ] **Step 4: Run all analyzer tests**

```bash
venv/bin/pytest tests/test_analyzer.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add news/nodes/analyzer.py tests/test_analyzer.py
git commit -m "feat: replace analyze_and_classify_node with classify_and_filter_node"
```

---

## Task 3: Rewrite sender — per-message send

**Files:**
- Modify: `news/nodes/sender.py`
- Modify: `tests/test_sender.py`

- [ ] **Step 1: Write failing tests**

Replace the entire `tests/test_sender.py` with:

```python
from unittest.mock import AsyncMock, call, patch

import news.config as config

STATE_WITH_SIGNALS = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [],
    "filtered_signals": [
        {"title": "LangGraph 2.0", "classification": "ai_agent_framework", "summary": "LangGraph major release", "source": "telegram"},
        {"title": "AutoGen update", "classification": "ai_agent_framework", "summary": "AutoGen 0.4 released", "source": "telegram"},
    ],
}

STATE_EMPTY = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [],
    "filtered_signals": [],
}


async def test_sends_each_filtered_signal_as_separate_message():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        result = await sender_node(STATE_WITH_SIGNALS)

    assert mock_bot.send_message.call_count == 2
    mock_bot.send_message.assert_any_call(
        chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
        text="LangGraph major release",
    )
    mock_bot.send_message.assert_any_call(
        chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
        text="AutoGen 0.4 released",
    )
    assert result == {}


async def test_sends_nothing_when_filtered_signals_empty():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        result = await sender_node(STATE_EMPTY)

    mock_bot.send_message.assert_not_called()
    assert result == {}


async def test_returns_empty_dict():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        result = await sender_node(STATE_EMPTY)

    assert result == {}
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_sender.py::test_sends_each_filtered_signal_as_separate_message -v
```

Expected: FAIL — the current sender reads `state["analysis"]` (a string), not `state["filtered_signals"]`

- [ ] **Step 3: Rewrite news/nodes/sender.py**

Replace the entire file with:

```python
import logging

from telegram import Bot

import news.config as config
from news.state import State

log = logging.getLogger(__name__)

_bot = Bot(token=config.TELEGRAM_BOT_TOKEN)


async def sender_node(state: State) -> dict:
    for signal in state["filtered_signals"]:
        await _bot.send_message(
            chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
            text=signal["summary"],
        )
    return {}
```

- [ ] **Step 4: Run all sender tests**

```bash
venv/bin/pytest tests/test_sender.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add news/nodes/sender.py tests/test_sender.py
git commit -m "feat: sender iterates filtered_signals and sends each summary"
```

---

## Task 4: Update graph, runner, and graph tests

**Files:**
- Modify: `news/graph.py`
- Modify: `news/runner.py`
- Modify: `tests/test_graph.py`

- [ ] **Step 1: Write failing graph test**

Replace the entire `tests/test_graph.py` with:

```python
from unittest.mock import AsyncMock, MagicMock, patch


async def test_graph_builder_has_correct_nodes():
    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            from news.graph import create_graph
            builder = create_graph()

    assert "telegram_collector" in builder.nodes
    assert "classify_and_filter" in builder.nodes
    assert "sender" in builder.nodes
    assert "analyze_and_classify" not in builder.nodes


async def test_full_graph_routes_dev_tool_signals_to_sender():
    tg_signals = [{"title": "LangGraph", "classification": "other", "summary": "LangGraph news", "source": "telegram"}]
    filtered = [{"title": "LangGraph", "classification": "ai_agent_framework", "summary": "LangGraph news", "source": "telegram"}]

    mock_tg = AsyncMock(return_value={"telegram_offset_id": 200, "signals": tg_signals})
    mock_classify = AsyncMock(return_value={"filtered_signals": filtered})
    mock_send = AsyncMock(return_value={})

    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            with patch("news.graph.telegram_collector_node", mock_tg):
                with patch("news.graph.classify_and_filter_node", mock_classify):
                    with patch("news.graph.sender_node", mock_send):
                        from langgraph.checkpoint.memory import MemorySaver
                        from news.graph import create_graph

                        graph = create_graph().compile(checkpointer=MemorySaver())
                        initial = {
                            "telegram_offset_id": 0,
                            "email_last_checked": 0.0,
                            "signals": [],
                            "filtered_signals": [],
                        }
                        result = await graph.ainvoke(
                            initial,
                            config={"configurable": {"thread_id": "test"}},
                        )

    assert result["filtered_signals"] == filtered
    assert result["telegram_offset_id"] == 200


async def test_telegram_collector_resolves_peer_before_fetching_history():
    """get_chat must be called before get_chat_history to warm pyrogram's peer cache."""
    call_order = []

    async def fake_get_chat(_chat_id):
        call_order.append("get_chat")

    async def fake_history(*_args, **_kwargs):
        call_order.append("get_chat_history")
        return
        yield

    mock_client = MagicMock()
    mock_client.get_chat = fake_get_chat
    mock_client.get_chat_history = fake_history

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=ctx):
        from news.nodes.telegram_collector import telegram_collector_node
        await telegram_collector_node({"telegram_offset_id": 0, "signals": []})

    assert call_order == ["get_chat", "get_chat_history"]
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_graph.py::test_graph_builder_has_correct_nodes -v
```

Expected: FAIL — `AssertionError: assert 'classify_and_filter' in builder.nodes`

- [ ] **Step 3: Update news/graph.py**

Replace the entire file with:

```python
from langgraph.graph import END, START, StateGraph

from news.nodes.analyzer import classify_and_filter_node
# TODO: re-enable email collector
# from news.nodes.email_collector import email_collector_node
from news.nodes.sender import sender_node
from news.nodes.telegram_collector import telegram_collector_node
from news.state import State


def create_graph() -> StateGraph:
    builder = StateGraph(State)

    builder.add_node("telegram_collector", telegram_collector_node)
    # TODO: re-enable email collector
    # builder.add_node("email_collector", email_collector_node)
    builder.add_node("classify_and_filter", classify_and_filter_node)
    builder.add_node("sender", sender_node)

    builder.add_edge(START, "telegram_collector")
    # TODO: re-enable email collector
    # builder.add_edge(START, "email_collector")
    builder.add_edge("telegram_collector", "classify_and_filter")
    # TODO: re-enable email collector
    # builder.add_edge("email_collector", "classify_and_filter")
    builder.add_edge("classify_and_filter", "sender")
    builder.add_edge("sender", END)

    return builder
```

- [ ] **Step 4: Update news/runner.py**

In `news/runner.py`, replace `_INITIAL_STATE`:

```python
_INITIAL_STATE: State = {
    "telegram_offset_id": 0,
    "email_last_checked": time.time(),
    "signals": [],
    "filtered_signals": [],
}
```

- [ ] **Step 5: Run the full test suite**

```bash
venv/bin/pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add news/graph.py news/runner.py tests/test_graph.py
git commit -m "feat: wire classify_and_filter into graph, update runner initial state"
```
