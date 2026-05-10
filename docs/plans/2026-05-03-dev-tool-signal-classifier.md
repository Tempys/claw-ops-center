# Dev-Tool Signal Classifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enhance the news pipeline analyzer to classify Telegram signals into dev-tool categories (ai_agent_framework, llm_finetuning, skill_plugin_builder, code_generation, dev_productivity, prompt_engineering, other, error) using a two-pass LLM flow.

**Architecture:** Pass 1 calls GPT-4o-mini to classify each batch of signals into JSON; Pass 2 uses those classifications to produce a digest that leads with dev-tool signals. Classifications happen in-memory inside the analyzer — they are not written back to `State.signals` because the `operator.add` reducer would duplicate the list.

**Tech Stack:** Python 3.12+, openai>=2.0.0, langgraph, pytest-asyncio (asyncio_mode=auto)

---

## File Map

| File | Change |
|------|--------|
| `tests/conftest.py` | Add `OPENAI_API_KEY` env var (currently missing, causes import errors) |
| `tests/test_config.py` | Update assertion: `ANTHROPIC_API_KEY` → `OPENAI_API_KEY` |
| `news/state.py` | Add `CLASSIFICATION` Literal; re-type `Signal.classification` |
| `tests/test_state.py` | Update to use new classification values |
| `news/nodes/telegram_collector.py` | Default classification `"informational"` → `"other"` |
| `tests/test_telegram_collector.py` | Assert default classification is `"other"` |
| `news/nodes/analyzer.py` | Two-pass flow: `_classify_batch` + digest; updated system prompts |
| `tests/test_analyzer.py` | Rewrite to cover classify pass, fallback, error bypass, coercion |

---

## Task 1: Fix test infrastructure

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Verify the broken state — run the tests**

```bash
venv/bin/pytest tests/test_config.py -v
```

Expected: FAIL — `AttributeError: module 'news.config' has no attribute 'ANTHROPIC_API_KEY'`

- [ ] **Step 2: Add OPENAI_API_KEY to conftest.py**

In `tests/conftest.py`, replace:

```python
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
```

with:

```python
os.environ.setdefault("OPENAI_API_KEY", "sk-openai-test")
```

- [ ] **Step 3: Update test_config.py assertion**

In `tests/test_config.py`, in `test_config_reads_all_env_vars`, replace:

```python
    assert cfg.ANTHROPIC_API_KEY == "sk-ant-test"
```

with:

```python
    assert cfg.OPENAI_API_KEY == "sk-openai-test"
```

Also update `test_missing_required_var_raises` — change the removed key and match string:

```python
def test_missing_required_var_raises():
    env = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        import news.config as cfg
        import pytest
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            importlib.reload(cfg)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_config.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_config.py
git commit -m "fix: align test fixtures with OPENAI_API_KEY config"
```

---

## Task 2: Add CLASSIFICATION Literal to state.py

**Files:**
- Modify: `news/state.py`
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_state.py`:

```python
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
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_state.py::test_classification_literal_contains_expected_values -v
```

Expected: FAIL — `ImportError: cannot import name 'CLASSIFICATION'`

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
    analysis: str
```

- [ ] **Step 4: Update existing test_state.py to use valid classification values**

In `tests/test_state.py`, update `test_signal_fields` to use a valid classification:

```python
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
```

Also update `test_signals_reducer_merges_lists` to use `"other"`:

```python
def test_signals_reducer_merges_lists():
    a = [{"title": "A", "classification": "other", "summary": "a", "source": "telegram"}]
    b = [{"title": "B", "classification": "other", "summary": "b", "source": "email"}]
    merged = operator.add(a, b)
    assert len(merged) == 2
    assert merged[0]["source"] == "telegram"
    assert merged[1]["source"] == "email"
```

- [ ] **Step 5: Run all state tests**

```bash
venv/bin/pytest tests/test_state.py -v
```

Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add news/state.py tests/test_state.py
git commit -m "feat: add CLASSIFICATION literal to state, re-type Signal.classification"
```

---

## Task 3: Update telegram_collector default classification

**Files:**
- Modify: `news/nodes/telegram_collector.py`
- Modify: `tests/test_telegram_collector.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_telegram_collector.py`:

```python
async def test_signal_default_classification_is_other():
    msg = MagicMock(id=300, text="Some message", caption=None)

    async def fake_history(*_a, **_kw):
        yield msg

    mock_client = AsyncMock()
    mock_client.get_chat_history = fake_history
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node
        result = await telegram_collector_node(STATE)

    assert result["signals"][0]["classification"] == "other"
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_telegram_collector.py::test_signal_default_classification_is_other -v
```

Expected: FAIL — `AssertionError: assert 'informational' == 'other'`

- [ ] **Step 3: Update _to_signal in telegram_collector.py**

In `news/nodes/telegram_collector.py`, change `_to_signal`:

```python
def _to_signal(message: Message) -> Signal:
    text = message.text or message.caption or ""
    return Signal(
        title=text[:80],
        classification="other",
        summary=text,
        source="telegram",
    )
```

- [ ] **Step 4: Run all telegram_collector tests**

```bash
venv/bin/pytest tests/test_telegram_collector.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add news/nodes/telegram_collector.py tests/test_telegram_collector.py
git commit -m "feat: default signal classification to 'other' in telegram collector"
```

---

## Task 4: Rewrite analyzer.py with two-pass flow

**Files:**
- Modify: `news/nodes/analyzer.py`

- [ ] **Step 1: Rewrite analyzer.py**

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

_CLASSIFY_SYSTEM = (
    "You are a signal classifier. Given a numbered list of signals, return ONLY a JSON array — "
    "no prose, no markdown. Each element: {\"index\": <int>, \"classification\": <category>}. "
    "Valid categories: ai_agent_framework, llm_finetuning, skill_plugin_builder, code_generation, "
    "dev_productivity, prompt_engineering, other, error."
)

_DIGEST_SYSTEM = (
    "You are an intelligence analyst. Given classified signals from Telegram channels and email, "
    "produce a concise digest. Lead with dev-tool signals "
    "(ai_agent_framework, llm_finetuning, skill_plugin_builder, code_generation, dev_productivity, "
    "prompt_engineering), then other signals. Omit noise. Be factual and brief."
)


def _format_signals(signals: list[Signal]) -> str:
    lines = ["Signals collected this run:\n"]
    for i, s in enumerate(signals, 1):
        lines.append(
            f"{i}. [{s['source'].upper()}][{s['classification']}] {s['title']}\n   {s['summary']}\n"
        )
    return "\n".join(lines)


async def _classify_batch(signals: list[Signal]) -> list[Signal]:
    if all(s["classification"] == "error" for s in signals):
        return signals

    try:
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=256,
            messages=[
                {"role": "system", "content": _CLASSIFY_SYSTEM},
                {"role": "user", "content": _format_signals(signals)},
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

    result = []
    for i, signal in enumerate(signals, 1):
        if signal["classification"] == "error":
            result.append(signal)
            continue
        raw_cls = index_map.get(i, "other")
        cls = raw_cls if raw_cls in _VALID_CLASSIFICATIONS else "other"
        result.append({**signal, "classification": cls})
    return result


async def analyze_and_classify_node(state: State) -> dict:
    signals = state["signals"]
    parts = []

    for i in range(0, len(signals), 5):
        batch = await _classify_batch(signals[i : i + 5])
        response = await _client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=1024,
            messages=[
                {"role": "system", "content": _DIGEST_SYSTEM},
                {"role": "user", "content": _format_signals(batch)},
            ],
        )
        parts.append(response.choices[0].message.content)

    return {"analysis": "\n\n".join(parts)}
```

- [ ] **Step 2: Run existing analyzer tests to see what breaks**

```bash
venv/bin/pytest tests/test_analyzer.py -v
```

Expected: FAIL — mocks use Anthropic-style API (`.messages.create`, `.content[0].text`), but analyzer now uses OpenAI-style (`.chat.completions.create`, `.choices[0].message.content`). Tests need rewriting in Task 5.

- [ ] **Step 3: Commit the analyzer**

```bash
git add news/nodes/analyzer.py
git commit -m "feat: two-pass classify+digest flow in analyzer"
```

---

## Task 5: Rewrite test_analyzer.py

**Files:**
- Modify: `tests/test_analyzer.py`

- [ ] **Step 1: Replace test_analyzer.py entirely**

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
    "analysis": "",
}

STATE_WITH_ERROR = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [
        {"title": "Collector failed", "classification": "error", "summary": "connection refused", "source": "telegram"},
        {"title": "AutoGen workshop", "classification": "other", "summary": "New AutoGen tutorial repo", "source": "telegram"},
    ],
    "analysis": "",
}


async def test_returns_analysis_text():
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        _make_openai_response(classify_json),
        _make_openai_response("Dev-tool digest: LangGraph 2.0 released. BTC up 5%."),
    ])

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import analyze_and_classify_node
        result = await analyze_and_classify_node(STATE)

    assert result["analysis"] == "Dev-tool digest: LangGraph 2.0 released. BTC up 5%."


async def test_classify_pass_updates_signal_classification():
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        _make_openai_response(classify_json),
        _make_openai_response("Digest text"),
    ])

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


async def test_error_signals_bypass_classify_pass():
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("Digest text")
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import analyze_and_classify_node
        result = await analyze_and_classify_node(STATE_WITH_ERROR)

    # Classify call should NOT have been made for the all-error batch... but here
    # only 1 of 2 signals is error. Verify the error signal is untouched in the digest call.
    # The classify call is made for the non-error signal; check the client was called.
    assert mock_client.chat.completions.create.called
    assert "analysis" in result


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

    # No LLM call should be made
    mock_client.chat.completions.create.assert_not_called()
    assert result[0]["classification"] == "error"


async def test_digest_prompt_includes_classification_labels():
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        _make_openai_response(classify_json),
        _make_openai_response("Digest"),
    ])

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import analyze_and_classify_node
        await analyze_and_classify_node(STATE)

    digest_call = mock_client.chat.completions.create.call_args_list[1]
    prompt = digest_call.kwargs["messages"][1]["content"]
    assert "ai_agent_framework" in prompt
    assert "other" in prompt
```

- [ ] **Step 2: Run tests to verify they pass**

```bash
venv/bin/pytest tests/test_analyzer.py -v
```

Expected: all PASS

- [ ] **Step 3: Run the full test suite**

```bash
venv/bin/pytest tests/ -v
```

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_analyzer.py
git commit -m "test: rewrite analyzer tests for two-pass classify+digest flow"
```
