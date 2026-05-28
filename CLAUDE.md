# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

`claw-ops-center` is a LangGraph pipeline that scans dev-tool "signals" from a Telegram channel and email (IMAP), enriches them, classifies them with OpenAI, and forwards the relevant ones to a Telegram destination chat via a bot. It is designed to run repeatedly on a schedule, remembering what it already processed between runs.

## Commands

Uses `uv` (see `uv.lock`). Prefix everything with `uv run`.

- **Run the pipeline once (production):** `uv run python -m news.runner` — uses the SQLite checkpointer at `CHECKPOINT_DB_PATH`.
- **Dev server / LangGraph Studio:** `uv run langgraph dev` — loads the `news` graph via `langgraph.json` → `news/graph.py:make_graph` (no checkpointer).
- **All tests:** `uv run pytest`
- **Single test:** `uv run pytest tests/test_graph.py::test_graph_has_expected_nodes`
- **Lint + format (also runs on commit):** `uv run pre-commit run --all-files` (ruff with `--fix`, then ruff-format).
- **Generate a Telegram session string** (one-time, for the user account that reads the channel): `uv run python scripts/gen_session.py`, then paste output into `.env`.

Tests need no real credentials — `tests/conftest.py` seeds dummy env vars before any import so `news/config.py` does not raise. `pytest.ini_options` sets `asyncio_mode = "auto"`, so `async def test_*` functions run without an explicit marker.

## Architecture

**Graph topology** (`news/graph.py`): two sub-pipelines fan out from `START` in parallel, both feed a `merge` node, which conditionally routes to `sender` only if `filtered_signals` is non-empty.

```
START ─┬─> telegram_pipeline ─┐
       └─> email_pipeline ─────┴─> merge ─(if filtered_signals)─> sender ─> END
```

- **Telegram pipeline** (`news/pipelines/telegram.py`): `collect` (pull recent channel messages via Pyrogram, extract URLs) → `enrich` (`telegram_extractor.py`: regex out GitHub links, fetch README excerpts over HTTP) → `analyze` (`telegram_analyzer.py`: OpenAI structured-output classification).
- **Email pipeline** (`news/pipelines/email.py`): `collect` (`gmail_client.py`: Gmail API + OAuth2 — fetch by `_build_query` filters, parse HTML/plain bodies, map to signal dicts) → `dedup` (sha256 of URL against `email_seen_hashes`) → `analyze`. Email signals are dicts of `{url, title, summary, source}` (richer than the bare `Signal` type); the URL is the Gmail permalink and is what dedup hashes. The collector degrades to `[]` when no OAuth token exists, so the rest of the run still proceeds.

**State & persistence** (`news/state.py`, `news/runner.py`) — the part that requires reading multiple files to understand:

- `State` is a `TypedDict`. Fields written by parallel branches use `Annotated[..., reducer]` so LangGraph knows how to merge concurrent writes: `_take_max` (timestamps), `_list_union` (dedup hashes), `_replace_or_add` (signal lists).
- `_replace_or_add` resets to `[]` when handed `None`. The runner exploits this: passing `filtered_signals: None` in the run input clears last run's results, while letting parallel branches accumulate within a run.
- Persistence is via `AsyncSqliteSaver`, single thread `thread_id="main"`. **`telegram_offset_id` is intentionally NOT in the run input** — the checkpointer owns it across runs so each run continues from the last-seen message. The first-ever run (no checkpoint) is seeded with `telegram_offset_id: 0` via `_FIRST_RUN_SEED`.
- Sub-graph states (`TelegramPipelineState`, `EmailState`) extend/scope `State` with transient fields that only live inside their pipeline.

## Conventions

- **Config access:** never read env vars directly. `news/config.py` validates a pydantic `Settings` at import time and exposes fields via module `__getattr__` — use `import news.config as config` then `config.OPENAI_API_KEY`. Adding a setting means adding a field to `Settings`.
- **Lazy heavy imports:** Pyrogram and `python-telegram-bot` are imported *inside* functions (see `telegram_collector.make_client`), not at module top, to keep import cheap and dodge event-loop init issues. `news/runner.py` creates a fresh event loop before importing anything for the same reason — keep the import ordering / `# noqa: E402` there intact.
- **Prompts** live as `.md` files in `news/prompts/templates/` and are loaded with `load_prompt(name, **kwargs)` (`str.format` substitution). Edit prompt text in the templates, not in Python.
- **Two classification styles:** the Telegram analyzer uses OpenAI structured output (`beta.chat.completions.parse` + a Pydantic `ClassificationResult`); the shared/email path (`news/nodes/analyzer.py:_classify_batch`) uses plain JSON parsing with a fallback to `"other"`. Both filter out `"other"`/`"error"` so only real dev-tool signals reach the sender. Model is `gpt-4o-mini` throughout.
- **Nodes return partial dict updates**, never the full state, and swallow/log their own errors so one failing source doesn't abort the whole run.

## Design docs

`docs/` holds dated design notes and plans (e.g. `docs/superpowers/specs/`, `docs/plans/`). Consult these for the rationale behind a node before changing its behavior.