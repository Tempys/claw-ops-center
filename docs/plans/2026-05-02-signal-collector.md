# Signal Collector Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a cron-driven LangGraph pipeline that collects Telegram channel messages and emails in parallel, runs LLM analysis and classification, and sends a digest to a Telegram channel.

**Architecture:** Parallel fan-out from `START` to `telegram_collector` and `email_collector` nodes; both write `Signal` objects into shared state via an `operator.add` reducer; fan-in at `analyze_and_classify` (Anthropic LLM); then `sender` posts the digest. Telegram `offset_id` and `email_last_checked` cursors live in graph state and are persisted across cron runs via `AsyncSqliteSaver`.

**Tech Stack:** LangGraph 1.1.10, Anthropic SDK 0.94.0, pyrogram (MTProto), python-telegram-bot 22.7, imaplib (stdlib), python-dotenv 1.2.2, pytest 9.0.3, pytest-asyncio 1.3.0

---

## File Map

| File | Responsibility |
|---|---|
| `openclaw/state.py` | `Signal` and `State` TypedDicts |
| `openclaw/config.py` | Env var loading via python-dotenv |
| `openclaw/nodes/telegram_collector.py` | pyrogram channel reader node |
| `openclaw/nodes/email_collector.py` | IMAP email reader node |
| `openclaw/nodes/analyzer.py` | Anthropic LLM analysis node |
| `openclaw/nodes/sender.py` | python-telegram-bot sender node |
| `openclaw/graph.py` | `StateGraph` construction |
| `openclaw/runner.py` | Async cron entrypoint |
| `tests/conftest.py` | Test env vars set before any imports |
| `tests/test_state.py` | State schema tests |
| `tests/test_config.py` | Config loading tests |
| `tests/test_telegram_collector.py` | Collector node tests (mocked pyrogram) |
| `tests/test_email_collector.py` | Collector node tests (mocked imaplib) |
| `tests/test_analyzer.py` | Analyzer node tests (mocked Anthropic) |
| `tests/test_sender.py` | Sender node tests (mocked bot) |
| `tests/test_graph.py` | Graph topology + integration test |

---

### Task 1: Scaffolding

**Files:**
- Create: `.gitignore`
- Create: `requirements.txt`
- Create: `pytest.ini`
- Create: `.env.example`
- Create: `openclaw/__init__.py`
- Create: `openclaw/nodes/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`

- [ ] **Step 1: Create .gitignore**

`/Users/dmr/PycharmProjects/claw-ops-center/.gitignore`:
```
venv/
__pycache__/
*.pyc
.env
checkpoints.db
*.session
.idea/
.pytest_cache/
```

- [ ] **Step 2: Create requirements.txt**

`/Users/dmr/PycharmProjects/claw-ops-center/requirements.txt`:
```
langgraph==1.1.10
langgraph-checkpoint-sqlite==3.0.3
anthropic==0.94.0
python-telegram-bot==22.7
pyrogram==2.0.106
tgcrypto
python-dotenv==1.2.2
pytest==9.0.3
pytest-asyncio==1.3.0
```

- [ ] **Step 3: Create pytest.ini**

`/Users/dmr/PycharmProjects/claw-ops-center/pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

- [ ] **Step 4: Create .env.example**

`/Users/dmr/PycharmProjects/claw-ops-center/.env.example`:
```
TELEGRAM_API_ID=12345678
TELEGRAM_API_HASH=your_api_hash_here
TELEGRAM_CHANNEL_ID=-1001234567890
TELEGRAM_BOT_TOKEN=123456789:AABBccDDeeFF...
TELEGRAM_DESTINATION_CHAT_ID=-1009876543210
EMAIL_HOST=imap.gmail.com
EMAIL_PORT=993
EMAIL_USERNAME=you@gmail.com
EMAIL_PASSWORD=your_app_password
ANTHROPIC_API_KEY=sk-ant-...
CHECKPOINT_DB_PATH=checkpoints.db
```

- [ ] **Step 5: Create empty init files**

`openclaw/__init__.py` — empty file
`openclaw/nodes/__init__.py` — empty file
`tests/__init__.py` — empty file

- [ ] **Step 6: Create tests/conftest.py**

`tests/conftest.py`:
```python
import os

# Set before any module imports so config.py does not raise at import time.
os.environ.setdefault("TELEGRAM_API_ID", "12345678")
os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
os.environ.setdefault("TELEGRAM_CHANNEL_ID", "-1001234567890")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test_token")
os.environ.setdefault("TELEGRAM_DESTINATION_CHAT_ID", "-1009876543210")
os.environ.setdefault("EMAIL_HOST", "imap.test.com")
os.environ.setdefault("EMAIL_PORT", "993")
os.environ.setdefault("EMAIL_USERNAME", "test@test.com")
os.environ.setdefault("EMAIL_PASSWORD", "password")
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
os.environ.setdefault("CHECKPOINT_DB_PATH", ":memory:")
```

- [ ] **Step 7: Commit**

```bash
git add .gitignore requirements.txt pytest.ini .env.example news/__init__.py news/nodes/__init__.py tests/__init__.py tests/conftest.py
git commit -m "feat: scaffold project structure"
```

---

### Task 2: State Schema

**Files:**
- Create: `openclaw/state.py`
- Create: `tests/test_state.py`

- [ ] **Step 1: Write failing tests**

`tests/test_state.py`:

```python
import operator
from typing import get_type_hints


def test_signal_fields():
    from news.state import Signal
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
    from news.state import State
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
```

- [ ] **Step 2: Run to verify failure**

```bash
cd /Users/dmr/PycharmProjects/claw-ops-center && venv/bin/pytest tests/test_state.py -v
```
Expected: `ModuleNotFoundError: No module named 'openclaw.state'`

- [ ] **Step 3: Implement state.py**

`openclaw/state.py`:
```python
from typing import Annotated
import operator
from typing_extensions import TypedDict


class Signal(TypedDict):
    title: str
    classification: str  # "urgent" | "informational" | "noise" | "error"
    summary: str
    source: str          # "telegram" | "email"


class State(TypedDict):
    telegram_offset_id: int
    email_last_checked: float
    signals: Annotated[list[Signal], operator.add]
    analysis: str
```

- [ ] **Step 4: Run to verify pass**

```bash
venv/bin/pytest tests/test_state.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add news/state.py tests/test_state.py
git commit -m "feat: add State and Signal schema"
```

---

### Task 3: Config

**Files:**
- Create: `openclaw/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests**

`tests/test_config.py`:

```python
import importlib
import os
from unittest.mock import patch


def test_config_reads_all_env_vars():
    import news.config as cfg
    importlib.reload(cfg)
    assert cfg.TELEGRAM_API_ID == 12345678
    assert cfg.TELEGRAM_API_HASH == "test_hash"
    assert cfg.TELEGRAM_CHANNEL_ID == "-1001234567890"
    assert cfg.TELEGRAM_BOT_TOKEN == "123:test_token"
    assert cfg.TELEGRAM_DESTINATION_CHAT_ID == "-1009876543210"
    assert cfg.EMAIL_HOST == "imap.test.com"
    assert cfg.EMAIL_PORT == 993
    assert cfg.EMAIL_USERNAME == "test@test.com"
    assert cfg.EMAIL_PASSWORD == "password"
    assert cfg.ANTHROPIC_API_KEY == "sk-ant-test"


def test_config_default_checkpoint_path():
    env = dict(os.environ)
    env.pop("CHECKPOINT_DB_PATH", None)
    with patch.dict(os.environ, env, clear=True):
        import news.config as cfg
        importlib.reload(cfg)
        assert cfg.CHECKPOINT_DB_PATH == "checkpoints.db"


def test_missing_required_var_raises():
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        import news.config as cfg
        import pytest
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            importlib.reload(cfg)
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_config.py -v
```
Expected: `ModuleNotFoundError: No module named 'openclaw.config'`

- [ ] **Step 3: Implement config.py**

`openclaw/config.py`:
```python
import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Required environment variable {key!r} is not set")
    return val


TELEGRAM_API_ID: int = int(_require("TELEGRAM_API_ID"))
TELEGRAM_API_HASH: str = _require("TELEGRAM_API_HASH")
TELEGRAM_CHANNEL_ID: str = _require("TELEGRAM_CHANNEL_ID")
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_DESTINATION_CHAT_ID: str = _require("TELEGRAM_DESTINATION_CHAT_ID")
EMAIL_HOST: str = _require("EMAIL_HOST")
EMAIL_PORT: int = int(os.environ.get("EMAIL_PORT", "993"))
EMAIL_USERNAME: str = _require("EMAIL_USERNAME")
EMAIL_PASSWORD: str = _require("EMAIL_PASSWORD")
ANTHROPIC_API_KEY: str = _require("ANTHROPIC_API_KEY")
CHECKPOINT_DB_PATH: str = os.environ.get("CHECKPOINT_DB_PATH", "checkpoints.db")
```

- [ ] **Step 4: Run to verify pass**

```bash
venv/bin/pytest tests/test_config.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add news/config.py tests/test_config.py
git commit -m "feat: add config module"
```

---

### Task 4: Telegram Collector Node

**Files:**
- Create: `openclaw/nodes/telegram_collector.py`
- Create: `tests/test_telegram_collector.py`

- [ ] **Step 1: Write failing tests**

`tests/test_telegram_collector.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

STATE = {
    "telegram_offset_id": 100,
    "email_last_checked": 0.0,
    "signals": [],
    "analysis": "",
}


async def test_returns_signals_and_updates_offset():
    msg1 = MagicMock(id=200, text="Urgent: BTC liquidations spike", caption=None)
    msg2 = MagicMock(id=150, text="Weekly update published", caption=None)
    mock_client = AsyncMock()
    mock_client.get_chat_history = AsyncMock(return_value=[msg1, msg2])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node
        result = await telegram_collector_node(STATE)

    assert result["telegram_offset_id"] == 200
    assert len(result["signals"]) == 2
    assert result["signals"][0]["source"] == "telegram"
    assert result["signals"][0]["title"] == "Urgent: BTC liquidations spike"


async def test_returns_empty_dict_when_no_messages():
    mock_client = AsyncMock()
    mock_client.get_chat_history = AsyncMock(return_value=[])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node
        result = await telegram_collector_node(STATE)

    assert result == {}


async def test_returns_error_signal_and_preserves_offset_on_exception():
    mock_client = AsyncMock()
    mock_client.get_chat_history = AsyncMock(side_effect=Exception("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node
        result = await telegram_collector_node(STATE)

    assert "telegram_offset_id" not in result
    assert len(result["signals"]) == 1
    assert result["signals"][0]["classification"] == "error"
    assert result["signals"][0]["source"] == "telegram"
    assert "connection refused" in result["signals"][0]["summary"]
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_telegram_collector.py -v
```
Expected: `ModuleNotFoundError: No module named 'openclaw.nodes.telegram_collector'`

- [ ] **Step 3: Implement telegram_collector.py**

`openclaw/nodes/telegram_collector.py`:

```python
from pyrogram import Client

import news.config as config
from news.state import Signal, State


def make_client() -> Client:
    return Client(
        "claw_session",
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
    )


def _to_signal(message) -> Signal:
    text = message.text or message.caption or ""
    return Signal(
        title=text[:80],
        classification="informational",
        summary=text,
        source="telegram",
    )


async def telegram_collector_node(state: State) -> dict:
    try:
        async with make_client() as client:
            messages = await client.get_chat_history(
                config.TELEGRAM_CHANNEL_ID,
                limit=100,
                offset_id=state["telegram_offset_id"],
            )
        if not messages:
            return {}
        return {
            "telegram_offset_id": messages[0].id,
            "signals": [_to_signal(m) for m in messages],
        }
    except Exception as exc:
        return {
            "signals": [Signal(
                title="Telegram collector failed",
                classification="error",
                summary=str(exc),
                source="telegram",
            )]
        }
```

- [ ] **Step 4: Run to verify pass**

```bash
venv/bin/pytest tests/test_telegram_collector.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add news/nodes/telegram_collector.py tests/test_telegram_collector.py
git commit -m "feat: add telegram collector node"
```

---

### Task 5: Email Collector Node

**Files:**
- Create: `openclaw/nodes/email_collector.py`
- Create: `tests/test_email_collector.py`

- [ ] **Step 1: Write failing tests**

`tests/test_email_collector.py`:

```python
from unittest.mock import patch

STATE = {
    "telegram_offset_id": 0,
    "email_last_checked": 1000.0,
    "signals": [],
    "analysis": "",
}


async def test_returns_signals_and_updates_timestamp():
    fake_emails = [
        {"subject": "Market Alert", "body": "BTC up 10%", "sender": "alerts@example.com"},
        {"subject": "Weekly Digest", "body": "Top stories", "sender": "digest@example.com"},
    ]
    with patch("news.nodes.email_collector.fetch_emails_since", return_value=fake_emails):
        with patch("news.nodes.email_collector.time") as mock_time:
            mock_time.time.return_value = 9999.0
            from news.nodes.email_collector import email_collector_node
            result = await email_collector_node(STATE)

    assert result["email_last_checked"] == 9999.0
    assert len(result["signals"]) == 2
    assert result["signals"][0]["source"] == "email"
    assert result["signals"][0]["title"] == "Market Alert"
    assert result["signals"][1]["title"] == "Weekly Digest"


async def test_returns_empty_signals_when_no_emails():
    with patch("news.nodes.email_collector.fetch_emails_since", return_value=[]):
        with patch("news.nodes.email_collector.time") as mock_time:
            mock_time.time.return_value = 9999.0
            from news.nodes.email_collector import email_collector_node
            result = await email_collector_node(STATE)

    assert result["email_last_checked"] == 9999.0
    assert result["signals"] == []


async def test_returns_error_signal_and_preserves_timestamp_on_exception():
    with patch("news.nodes.email_collector.fetch_emails_since", side_effect=Exception("IMAP auth failed")):
        from news.nodes.email_collector import email_collector_node
        result = await email_collector_node(STATE)

    assert "email_last_checked" not in result
    assert len(result["signals"]) == 1
    assert result["signals"][0]["classification"] == "error"
    assert result["signals"][0]["source"] == "email"
    assert "IMAP auth failed" in result["signals"][0]["summary"]
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_email_collector.py -v
```
Expected: `ModuleNotFoundError: No module named 'openclaw.nodes.email_collector'`

- [ ] **Step 3: Implement email_collector.py**

`openclaw/nodes/email_collector.py`:

```python
import asyncio
import email
import imaplib
import time
from datetime import datetime
from email.header import decode_header as _raw_decode

import news.config as config
from news.state import Signal, State


def _decode(value) -> str:
    if value is None:
        return ""
    parts = _raw_decode(str(value))
    out = []
    for part, enc in parts:
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(part)
    return " ".join(out)


def _body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                return payload.decode("utf-8", errors="replace")[:1000] if payload else ""
    payload = msg.get_payload(decode=True)
    return payload.decode("utf-8", errors="replace")[:1000] if payload else ""


def fetch_emails_since(since_timestamp: float) -> list[dict]:
    since_date = datetime.fromtimestamp(since_timestamp).strftime("%d-%b-%Y")
    results = []
    with imaplib.IMAP4_SSL(config.EMAIL_HOST, config.EMAIL_PORT) as imap:
        imap.login(config.EMAIL_USERNAME, config.EMAIL_PASSWORD)
        imap.select("INBOX")
        _, msg_ids = imap.search(None, f"SINCE {since_date}")
        for msg_id in (msg_ids[0].split() if msg_ids[0] else []):
            _, data = imap.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            results.append({
                "subject": _decode(msg.get("Subject")),
                "body": _body(msg),
                "sender": _decode(msg.get("From")),
            })
    return results


async def email_collector_node(state: State) -> dict:
    try:
        now = time.time()
        emails = await asyncio.to_thread(fetch_emails_since, state["email_last_checked"])
        signals = [
            Signal(
                title=e["subject"] or "(no subject)",
                classification="informational",
                summary=e["body"],
                source="email",
            )
            for e in emails
        ]
        return {"email_last_checked": now, "signals": signals}
    except Exception as exc:
        return {
            "signals": [Signal(
                title="Email collector failed",
                classification="error",
                summary=str(exc),
                source="email",
            )]
        }
```

- [ ] **Step 4: Run to verify pass**

```bash
venv/bin/pytest tests/test_email_collector.py -v
```
Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add news/nodes/email_collector.py tests/test_email_collector.py
git commit -m "feat: add email collector node"
```

---

### Task 6: Analyzer Node

**Files:**
- Create: `openclaw/nodes/analyzer.py`
- Create: `tests/test_analyzer.py`

- [ ] **Step 1: Write failing tests**

`tests/test_analyzer.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

STATE = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [
        {"title": "BTC surges", "classification": "informational", "summary": "BTC up 15%", "source": "telegram"},
        {"title": "Volatility alert", "classification": "informational", "summary": "VIX spike", "source": "email"},
    ],
    "analysis": "",
}


async def test_returns_llm_analysis_text():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="URGENT: BTC up 15%. VIX spike warrants monitoring.")]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import analyze_and_classify_node
        result = await analyze_and_classify_node(STATE)

    assert result["analysis"] == "URGENT: BTC up 15%. VIX spike warrants monitoring."


async def test_prompt_includes_all_signals():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Summary")]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import analyze_and_classify_node
        await analyze_and_classify_node(STATE)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    prompt = call_kwargs["messages"][0]["content"]
    assert "BTC surges" in prompt
    assert "Volatility alert" in prompt
    assert "telegram" in prompt.lower()
    assert "email" in prompt.lower()
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_analyzer.py -v
```
Expected: `ModuleNotFoundError: No module named 'openclaw.nodes.analyzer'`

- [ ] **Step 3: Implement analyzer.py**

`openclaw/nodes/analyzer.py`:

```python
import anthropic

import news.config as config
from news.state import Signal, State

_client = anthropic.AsyncAnthropic(api_key=config.ANTHROPIC_API_KEY)

_SYSTEM = (
    "You are an intelligence analyst. Given signals collected from Telegram channels and email, "
    "produce a concise digest. Lead with urgent items, follow with informational, omit noise. "
    "Be factual and brief."
)


def _format_signals(signals: list[Signal]) -> str:
    lines = ["Signals collected this run:\n"]
    for i, s in enumerate(signals, 1):
        lines.append(f"{i}. [{s['source'].upper()}] {s['title']}\n   {s['summary']}\n")
    return "\n".join(lines)


async def analyze_and_classify_node(state: State) -> dict:
    response = await _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=_SYSTEM,
        messages=[{"role": "user", "content": _format_signals(state["signals"])}],
    )
    return {"analysis": response.content[0].text}
```

- [ ] **Step 4: Run to verify pass**

```bash
venv/bin/pytest tests/test_analyzer.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add news/nodes/analyzer.py tests/test_analyzer.py
git commit -m "feat: add LLM analyzer node"
```

---

### Task 7: Sender Node

**Files:**
- Create: `openclaw/nodes/sender.py`
- Create: `tests/test_sender.py`

- [ ] **Step 1: Write failing tests**

`tests/test_sender.py`:

```python
from unittest.mock import AsyncMock, patch

STATE = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [],
    "analysis": "URGENT: BTC up 15%. VIX spike detected.",
}


async def test_sends_analysis_to_destination_chat():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        import news.config as config
        result = await sender_node(STATE)

    mock_bot.send_message.assert_called_once_with(
        chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
        text="URGENT: BTC up 15%. VIX spike detected.",
    )
    assert result == {}


async def test_returns_empty_dict():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        result = await sender_node(STATE)

    assert result == {}
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_sender.py -v
```
Expected: `ModuleNotFoundError: No module named 'openclaw.nodes.sender'`

- [ ] **Step 3: Implement sender.py**

`openclaw/nodes/sender.py`:

```python
from telegram import Bot

import news.config as config
from news.state import State

_bot = Bot(token=config.TELEGRAM_BOT_TOKEN)


async def sender_node(state: State) -> dict:
    await _bot.send_message(
        chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
        text=state["analysis"],
    )
    return {}
```

- [ ] **Step 4: Run to verify pass**

```bash
venv/bin/pytest tests/test_sender.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add news/nodes/sender.py tests/test_sender.py
git commit -m "feat: add sender node"
```

---

### Task 8: Graph

**Files:**
- Create: `openclaw/graph.py`
- Create: `tests/test_graph.py`

- [ ] **Step 1: Write failing tests**

`tests/test_graph.py`:

```python
from unittest.mock import AsyncMock, patch


def test_graph_builder_has_correct_nodes():
    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            from news.graph import build_graph_builder
            builder = build_graph_builder()

    assert "telegram_collector" in builder.nodes
    assert "email_collector" in builder.nodes
    assert "analyze_and_classify" in builder.nodes
    assert "sender" in builder.nodes


async def test_full_graph_produces_analysis_from_both_sources():
    tg_signals = [{"title": "BTC up", "classification": "informational", "summary": "Up 10%", "source": "telegram"}]
    em_signals = [{"title": "Alert", "classification": "informational", "summary": "Volatility", "source": "email"}]

    mock_tg = AsyncMock(return_value={"telegram_offset_id": 200, "signals": tg_signals})
    mock_em = AsyncMock(return_value={"email_last_checked": 9999.0, "signals": em_signals})
    mock_analyze = AsyncMock(return_value={"analysis": "Urgent: BTC up 10%"})
    mock_send = AsyncMock(return_value={})

    with patch("news.nodes.telegram_collector.telegram_collector_node", mock_tg):
        with patch("news.nodes.email_collector.email_collector_node", mock_em):
            with patch("news.nodes.analyzer.analyze_and_classify_node", mock_analyze):
                with patch("news.nodes.sender.sender_node", mock_send):
                    with patch("news.nodes.analyzer._client", AsyncMock()):
                        with patch("news.nodes.sender._bot", AsyncMock()):
                            from langgraph.checkpoint.memory import MemorySaver
                            from news.graph import build_graph_builder

                            graph = build_graph_builder().compile(checkpointer=MemorySaver())
                            initial = {
                                "telegram_offset_id": 0,
                                "email_last_checked": 0.0,
                                "signals": [],
                                "analysis": "",
                            }
                            result = await graph.ainvoke(
                                initial,
                                config={"configurable": {"thread_id": "test"}},
                            )

    assert result["analysis"] == "Urgent: BTC up 10%"
    assert result["telegram_offset_id"] == 200
    assert result["email_last_checked"] == 9999.0
```

- [ ] **Step 2: Run to verify failure**

```bash
venv/bin/pytest tests/test_graph.py -v
```
Expected: `ModuleNotFoundError: No module named 'openclaw.graph'`

- [ ] **Step 3: Implement graph.py**

`openclaw/graph.py`:

```python
from langgraph.graph import END, START, StateGraph

from news.nodes.analyzer import analyze_and_classify_node
from news.nodes.email_collector import email_collector_node
from news.nodes.sender import sender_node
from news.nodes.telegram_collector import telegram_collector_node
from news.state import State


def build_graph_builder() -> StateGraph:
    builder = StateGraph(State)

    builder.add_node("telegram_collector", telegram_collector_node)
    builder.add_node("email_collector", email_collector_node)
    builder.add_node("analyze_and_classify", analyze_and_classify_node)
    builder.add_node("sender", sender_node)

    builder.add_edge(START, "telegram_collector")
    builder.add_edge(START, "email_collector")
    builder.add_edge("telegram_collector", "analyze_and_classify")
    builder.add_edge("email_collector", "analyze_and_classify")
    builder.add_edge("analyze_and_classify", "sender")
    builder.add_edge("sender", END)

    return builder
```

- [ ] **Step 4: Run to verify pass**

```bash
venv/bin/pytest tests/test_graph.py -v
```
Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add news/graph.py tests/test_graph.py
git commit -m "feat: add graph builder"
```

---

### Task 9: Runner

**Files:**
- Create: `openclaw/runner.py`

- [ ] **Step 1: Implement runner.py**

`openclaw/runner.py`:

```python
import asyncio
import logging

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

import news.config as config
from news.graph import build_graph_builder
from news.state import State

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_RUN_CONFIG = {"configurable": {"thread_id": "main"}}

_INITIAL_STATE: State = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [],
    "analysis": "",
}


async def main() -> None:
    async with AsyncSqliteSaver.from_conn_string(config.CHECKPOINT_DB_PATH) as checkpointer:
        graph = build_graph_builder().compile(checkpointer=checkpointer)
        try:
            await graph.ainvoke(_INITIAL_STATE, config=_RUN_CONFIG)
            log.info("Run completed successfully")
        except Exception as exc:
            log.error(f"Run failed: {exc}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: Verify import works**

```bash
venv/bin/python -c "from openclaw.runner import main; print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Run full suite**

```bash
venv/bin/pytest tests/ -v
```
Expected: all tests pass

- [ ] **Step 4: Commit**

```bash
git add news/runner.py
git commit -m "feat: add cron runner entrypoint"
```
