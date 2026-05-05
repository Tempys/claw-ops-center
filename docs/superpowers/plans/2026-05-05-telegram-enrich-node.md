# Telegram GitHub Enrich Node Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract GitHub README enrichment from `telegram_analyze_node` into a dedicated `telegram_enrich_node`, giving each LangGraph node a single responsibility aligned with the ReAct pattern.

**Architecture:** A new `telegram_enrich_node` sits between `dedup` and `analyze` in the telegram pipeline. It filters raw signals to those containing GitHub URLs, fetches README excerpts, and emits typed `EnrichedSignal` dicts. The analyzer receives pre-enriched signals and does pure LLM classification only — no HTTP calls.

**Tech Stack:** Python 3.12, LangGraph, httpx, openai, pytest-asyncio (asyncio_mode = auto)

---

### Task 1: Extend state.py with new schemas

**Files:**
- Modify: `news/state.py`
- Modify: `tests/test_state.py`

- [ ] **Step 1: Write failing tests for new types**

Add to the bottom of `tests/test_state.py`:

```python
def test_github_signal_fields():
    from news.state import GitHubSignal
    s: GitHubSignal = {
        "title": "OpenAI Agents",
        "summary": "https://github.com/openai/openai-agents",
        "source": "telegram",
        "repo_owner": "openai",
        "repo_name": "openai-agents",
    }
    assert s["repo_owner"] == "openai"
    assert s["repo_name"] == "openai-agents"


def test_enriched_signal_fields():
    from news.state import EnrichedSignal
    s: EnrichedSignal = {
        "title": "OpenAI Agents",
        "summary": "Check this out",
        "source": "telegram",
        "repo_owner": "openai",
        "repo_name": "openai-agents",
        "readme_excerpt": "# OpenAI Agents SDK",
    }
    assert s["readme_excerpt"] == "# OpenAI Agents SDK"


def test_state_has_telegram_enriched_signals_field():
    from news.state import State
    s: State = {
        "telegram_offset_id": 0,
        "telegram_raw_signals": [],
        "telegram_seen_hashes": [],
        "telegram_enriched_signals": [],
        "email_last_checked": 0.0,
        "email_raw_signals": [],
        "email_seen_hashes": [],
        "filtered_signals": [],
    }
    assert s["telegram_enriched_signals"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_state.py::test_github_signal_fields tests/test_state.py::test_enriched_signal_fields tests/test_state.py::test_state_has_telegram_enriched_signals_field -v
```

Expected: FAIL with `ImportError: cannot import name 'GitHubSignal'`

- [ ] **Step 3: Add types to state.py**

Replace the full content of `news/state.py` with:

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


class GitHubSignal(TypedDict):
    title: str
    summary: str
    source: str
    repo_owner: str
    repo_name: str


class EnrichedSignal(TypedDict):
    title: str
    summary: str
    source: str
    repo_owner: str
    repo_name: str
    readme_excerpt: str


def _list_union(a: list[str], b: list[str]) -> list[str]:
    """Merge two hash lists, preserving order and deduplicating."""
    seen = set(a)
    return a + [x for x in b if x not in seen]


class State(TypedDict):
    # Telegram pipeline
    telegram_offset_id: int
    telegram_raw_signals: list[Signal]
    telegram_seen_hashes: Annotated[list[str], _list_union]
    telegram_enriched_signals: list[EnrichedSignal]
    # Email pipeline
    email_last_checked: float
    email_raw_signals: list[Signal]
    email_seen_hashes: Annotated[list[str], _list_union]
    # Fan-in — both pipelines append here via operator.add
    filtered_signals: Annotated[list[Signal], operator.add]
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_state.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add news/state.py tests/test_state.py
git commit -m "feat: add GitHubSignal, EnrichedSignal and telegram_enriched_signals to state"
```

---

### Task 2: Create telegram_enricher.py

**Files:**
- Create: `news/nodes/telegram_enricher.py`
- Create: `tests/test_telegram_enricher.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_telegram_enricher.py`:

```python
# tests/test_telegram_enricher.py
from unittest.mock import AsyncMock, patch

_RAW_SIGNAL = {
    "title": "Check out https://github.com/openai/openai-agents",
    "classification": "other",
    "summary": "Check out https://github.com/openai/openai-agents",
    "source": "telegram",
}

_PLAIN_SIGNAL = {
    "title": "BTC is up",
    "classification": "other",
    "summary": "BTC up 5% today",
    "source": "telegram",
}

STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "telegram_enriched_signals": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_enrich_node_extracts_github_url_and_fetches_readme():
    readme = "# OpenAI Agents SDK\nBuild agents with Python."
    with patch("news.nodes.telegram_enricher._fetch_readme", AsyncMock(return_value=readme)):
        from news.nodes.telegram_enricher import telegram_enrich_node
        result = await telegram_enrich_node({**STATE_BASE, "telegram_raw_signals": [_RAW_SIGNAL]})

    assert len(result["telegram_enriched_signals"]) == 1
    sig = result["telegram_enriched_signals"][0]
    assert sig["repo_owner"] == "openai"
    assert sig["repo_name"] == "openai-agents"
    assert sig["readme_excerpt"] == readme


async def test_enrich_node_drops_plain_text_signals():
    with patch("news.nodes.telegram_enricher._fetch_readme", AsyncMock(return_value="readme")):
        from news.nodes.telegram_enricher import telegram_enrich_node
        result = await telegram_enrich_node({**STATE_BASE, "telegram_raw_signals": [_PLAIN_SIGNAL]})

    assert result["telegram_enriched_signals"] == []


async def test_enrich_node_drops_signal_when_readme_fetch_fails():
    with patch("news.nodes.telegram_enricher._fetch_readme", AsyncMock(return_value="")):
        from news.nodes.telegram_enricher import telegram_enrich_node
        result = await telegram_enrich_node({**STATE_BASE, "telegram_raw_signals": [_RAW_SIGNAL]})

    assert result["telegram_enriched_signals"] == []


async def test_enrich_node_strips_trailing_punctuation_from_repo_name():
    signal = {**_RAW_SIGNAL, "summary": "See https://github.com/openai/openai-agents."}
    with patch("news.nodes.telegram_enricher._fetch_readme", AsyncMock(return_value="# Agents")) as mock_fetch:
        from news.nodes.telegram_enricher import telegram_enrich_node
        await telegram_enrich_node({**STATE_BASE, "telegram_raw_signals": [signal]})

    mock_fetch.assert_awaited_once_with("openai", "openai-agents")


async def test_enrich_node_passes_correct_fields_to_enriched_signal():
    readme = "# Readme content"
    with patch("news.nodes.telegram_enricher._fetch_readme", AsyncMock(return_value=readme)):
        from news.nodes.telegram_enricher import telegram_enrich_node
        result = await telegram_enrich_node({**STATE_BASE, "telegram_raw_signals": [_RAW_SIGNAL]})

    sig = result["telegram_enriched_signals"][0]
    assert sig["title"] == _RAW_SIGNAL["title"]
    assert sig["summary"] == _RAW_SIGNAL["summary"]
    assert sig["source"] == "telegram"
    assert sig["readme_excerpt"] == readme
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_telegram_enricher.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'news.nodes.telegram_enricher'`

- [ ] **Step 3: Implement telegram_enricher.py**

Create `news/nodes/telegram_enricher.py`:

```python
import asyncio
import logging
import re

import httpx

from news.state import EnrichedSignal, GitHubSignal, Signal, State

log = logging.getLogger(__name__)

_GITHUB_RE = re.compile(
    r"https?://github\.com/([^/\s\)\"\'\#]+)/([^/\s\)\"\'\#]+)",
    re.IGNORECASE,
)


def _extract_github(signal: Signal) -> GitHubSignal | None:
    text = signal["summary"] or signal["title"]
    m = _GITHUB_RE.search(text)
    if not m:
        return None
    return GitHubSignal(
        title=signal["title"],
        summary=signal["summary"],
        source=signal["source"],
        repo_owner=m.group(1),
        repo_name=m.group(2).rstrip("./"),
    )


async def _fetch_readme(owner: str, repo: str) -> str:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            r = await http.get(url, follow_redirects=True)
            if r.status_code == 200:
                return r.text[:1500]
    except Exception:
        log.debug("README fetch failed for %s/%s", owner, repo)
    return ""


async def _enrich_one(signal: Signal) -> EnrichedSignal | None:
    gh = _extract_github(signal)
    if gh is None:
        return None
    readme = await _fetch_readme(gh["repo_owner"], gh["repo_name"])
    if not readme:
        return None
    return EnrichedSignal(
        title=gh["title"],
        summary=gh["summary"],
        source=gh["source"],
        repo_owner=gh["repo_owner"],
        repo_name=gh["repo_name"],
        readme_excerpt=readme,
    )


async def telegram_enrich_node(state: State) -> dict:
    signals = state["telegram_raw_signals"]
    results = await asyncio.gather(*(_enrich_one(s) for s in signals))
    return {"telegram_enriched_signals": [r for r in results if r is not None]}
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_telegram_enricher.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add news/nodes/telegram_enricher.py tests/test_telegram_enricher.py
git commit -m "feat: add telegram_enrich_node that extracts GitHub URLs and fetches README context"
```

---

### Task 3: Update telegram_analyzer.py and its tests

**Files:**
- Modify: `news/nodes/telegram_analyzer.py`
- Modify: `tests/test_telegram_analyzer.py`

The analyzer no longer handles HTTP or URL extraction. It reads `EnrichedSignal` from `telegram_enriched_signals` and does LLM classification only.

- [ ] **Step 1: Rewrite tests for the new contract**

Replace the full content of `tests/test_telegram_analyzer.py` with:

```python
# tests/test_telegram_analyzer.py
from unittest.mock import AsyncMock, MagicMock, patch


def _make_parse_response(cls: str, description: str = "A project", reason: str = "It fits") -> MagicMock:
    parsed = MagicMock()
    parsed.classification = cls
    parsed.description = description
    parsed.reason = reason
    message = MagicMock()
    message.parsed = parsed
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _enriched(title: str, summary: str, readme: str = "# Some README") -> dict:
    return {
        "title": title,
        "summary": summary,
        "source": "telegram",
        "repo_owner": "some-owner",
        "repo_name": "some-repo",
        "readme_excerpt": readme,
    }


STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "telegram_enriched_signals": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_analyze_node_classifies_enriched_signals():
    signals = [
        _enriched("LangGraph 2.0 drops", "Major LangGraph release"),
        _enriched("BTC up 5%", "Price update"),
    ]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(side_effect=[
        _make_parse_response("ai_agent_framework", "LangGraph agent framework", "Orchestrates LLM agents"),
        _make_parse_response("other"),
    ])

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    assert len(result["filtered_signals"]) == 1
    assert result["filtered_signals"][0]["classification"] == "ai_agent_framework"


async def test_analyze_node_returns_empty_when_all_other():
    signals = [_enriched("BTC up 5%", "Price update")]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(return_value=_make_parse_response("other"))

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    assert result["filtered_signals"] == []


async def test_analyze_node_builds_enriched_summary():
    signals = [_enriched("Tool X", "A new tool")]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_parse_response(
            "dev_productivity",
            "Tool X boosts developer workflow",
            "Directly improves dev productivity",
        )
    )

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    assert len(result["filtered_signals"]) == 1
    sig = result["filtered_signals"][0]
    assert "Tool X boosts developer workflow" in sig["summary"]
    assert "Directly improves dev productivity" in sig["summary"]


async def test_analyze_node_includes_readme_in_prompt():
    signals = [_enriched("Tool X", "A new tool", readme="# Tool X\nBoosts productivity dramatically.")]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_parse_response("dev_productivity")
    )

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    call_messages = mock_client.beta.chat.completions.parse.call_args.kwargs["messages"]
    user_content = next(m["content"] for m in call_messages if m["role"] == "user")
    assert "GitHub README excerpt" in user_content
    assert "Boosts productivity dramatically" in user_content


async def test_analyze_node_falls_back_on_llm_error():
    signals = [_enriched("Some tool", "A cool tool")]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API down"))

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    assert result["filtered_signals"] == []
```

- [ ] **Step 2: Run tests to verify they fail**

```
pytest tests/test_telegram_analyzer.py -v
```

Expected: FAIL — analyzer still reads `telegram_raw_signals` and still imports `_fetch_github_readme`

- [ ] **Step 3: Rewrite telegram_analyzer.py**

Replace the full content of `news/nodes/telegram_analyzer.py` with:

```python
# news/nodes/telegram_analyzer.py
import asyncio
import logging
from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel

import news.config as config
from news.state import EnrichedSignal, Signal, State

log = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=config.OPENAI_API_KEY)
_MODEL = "gpt-4o-mini"

_CATEGORIES = [
    "ai_agent_framework",
    "llm_finetuning",
    "skill_plugin_builder",
    "code_generation",
    "dev_productivity",
    "prompt_engineering",
    "other",
]

_VALID = set(_CATEGORIES)

_SYSTEM = (
    "You are a signal classifier for a curated ML/AI Telegram channel. "
    "Posts are short — often just a title, a URL, or a few sentences. "
    "The channel is tech-focused: classify borderline posts rather than defaulting to 'other'.\n\n"
    "Given a Telegram post and optional GitHub repository context, return JSON with:\n"
    "- classification: the most fitting category\n"
    "- description: one sentence describing what the project or post is about\n"
    "- reason: one sentence explaining why it fits the chosen category\n\n"
    "Valid categories: ai_agent_framework, llm_finetuning, skill_plugin_builder, "
    "code_generation, dev_productivity, prompt_engineering, other."
)


class ClassificationResult(BaseModel):
    classification: Literal[
        "ai_agent_framework",
        "llm_finetuning",
        "skill_plugin_builder",
        "code_generation",
        "dev_productivity",
        "prompt_engineering",
        "other",
    ]
    description: str
    reason: str


async def _classify_one(signal: EnrichedSignal) -> Signal:
    text = signal["summary"] or signal["title"]
    github_block = f"\n\nGitHub README excerpt:\n{signal['readme_excerpt']}"

    try:
        resp = await _client.beta.chat.completions.parse(
            model=_MODEL,
            max_tokens=256,
            messages=[
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": f"Post:\n{text}{github_block}"},
            ],
            response_format=ClassificationResult,
        )
        result = resp.choices[0].message.parsed
        cls = result.classification if result.classification in _VALID else "other"
        enriched_summary = f"{result.description} — {result.reason}".strip(" —")
        return Signal(
            title=signal["title"],
            classification=cls,
            summary=enriched_summary,
            source=signal["source"],
        )
    except Exception:
        log.warning("Classification failed: %s", signal["title"][:60], exc_info=True)
        return Signal(
            title=signal["title"],
            classification="other",
            summary=signal["summary"],
            source=signal["source"],
        )


async def telegram_analyze_node(state: State) -> dict:
    signals = state["telegram_enriched_signals"][:10]
    classified = await asyncio.gather(*(_classify_one(s) for s in signals))
    filtered = [s for s in classified if s["classification"] not in {"other", "error"}]
    return {"filtered_signals": list(filtered)}
```

- [ ] **Step 4: Run tests to verify they pass**

```
pytest tests/test_telegram_analyzer.py -v
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add news/nodes/telegram_analyzer.py tests/test_telegram_analyzer.py
git commit -m "refactor: telegram_analyze_node reads EnrichedSignal, removes HTTP enrichment logic"
```

---

### Task 4: Wire enrich node into pipeline and update STATE_BASE

**Files:**
- Modify: `news/pipelines/telegram.py`
- Modify: `tests/test_graph.py`

- [ ] **Step 1: Add telegram_enriched_signals to STATE_BASE in test_graph.py**

In `tests/test_graph.py`, replace the `STATE_BASE` dict with:

```python
STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "telegram_enriched_signals": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}
```

- [ ] **Step 2: Insert enrich node into the pipeline**

Replace the full content of `news/pipelines/telegram.py` with:

```python
# news/pipelines/telegram.py
from langgraph.graph import END, START, StateGraph

from news.nodes.telegram_collector import telegram_collector_node
from news.nodes.telegram_dedup import telegram_dedup_node
from news.nodes.telegram_enricher import telegram_enrich_node
from news.nodes.telegram_analyzer import telegram_analyze_node
from news.state import State


def build_telegram_pipeline():
    builder = StateGraph(State)
    builder.add_node("collect", telegram_collector_node)
    builder.add_node("dedup", telegram_dedup_node)
    builder.add_node("enrich", telegram_enrich_node)
    builder.add_node("analyze", telegram_analyze_node)
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "dedup")
    builder.add_edge("dedup", "enrich")
    builder.add_edge("enrich", "analyze")
    builder.add_edge("analyze", END)
    return builder.compile()
```

- [ ] **Step 3: Run full test suite**

```
pytest -v
```

Expected: all PASS

- [ ] **Step 4: Commit**

```bash
git add news/pipelines/telegram.py tests/test_graph.py
git commit -m "feat: wire telegram_enrich_node into pipeline between dedup and analyze"
```
