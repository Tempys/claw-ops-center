# Design: Telegram GitHub Enrich Node

**Date:** 2026-05-05
**Branch:** feature/signal-collector

## Problem

`telegram_analyzer.py::_classify_one` currently does two distinct things:

1. Extracts a GitHub URL from signal text and fetches the README (I/O enrichment)
2. Classifies the signal using an LLM (inference)

This violates the single-responsibility principle and the ReAct pattern — the observation step (fetch external context) and the reasoning step (classify) should be separate nodes.

## Approach

Extract GitHub enrichment into a dedicated `telegram_enrich_node` LangGraph node. The pipeline becomes:

```
collect → dedup → enrich → analyze
```

The enrich node filters to GitHub-linked signals only and fetches README context. The analyze node receives pre-enriched signals and does pure LLM classification.

## Schemas

### GitHubSignal

Input to the enrich node — created when a GitHub URL is found in a raw signal:

```python
class GitHubSignal(TypedDict):
    title: str
    summary: str
    source: str
    repo_owner: str
    repo_name: str
```

### EnrichedSignal

Output of the enrich node — carries the fetched README excerpt:

```python
class EnrichedSignal(TypedDict):
    title: str
    summary: str
    source: str
    repo_owner: str
    repo_name: str
    readme_excerpt: str
```

## State Change

Add one key to `State` in `state.py`:

```python
telegram_enriched_signals: list[EnrichedSignal]
```

`telegram_raw_signals` remains as-is (output of collector). `telegram_enriched_signals` is the handoff between enrich and analyze.

## Node Responsibilities

| Node | Input state key | Output state key | Responsibility |
|---|---|---|---|
| `telegram_enrich_node` | `telegram_raw_signals` | `telegram_enriched_signals` | Extract GitHub URL, fetch README, drop non-GitHub signals |
| `telegram_analyze_node` | `telegram_enriched_signals` | `filtered_signals` | LLM classification only |

## Files

| File | Change |
|---|---|
| `news/nodes/telegram_enricher.py` | New file — `_GITHUB_RE`, `_fetch_github_readme`, `telegram_enrich_node` |
| `news/nodes/telegram_analyzer.py` | Remove enrichment logic, read from `telegram_enriched_signals` |
| `news/pipelines/telegram.py` | Insert `enrich` node between `dedup` and `analyze` |
| `news/state.py` | Add `telegram_enriched_signals: list[EnrichedSignal]`, define `GitHubSignal`, `EnrichedSignal` |

## ReAct Alignment

| ReAct step | Node |
|---|---|
| Observe | `telegram_collector_node` — fetch raw messages |
| Reason | `telegram_enrich_node` — detect GitHub URL |
| Act | `telegram_enrich_node` — fetch README (external tool call) |
| Observe | `telegram_enriched_signals` — typed enrichment result |
| Reason | `telegram_analyze_node` — classify with full context |

## Error Handling

- If the README fetch fails (network timeout, 404), the signal is dropped — no partial `EnrichedSignal` with empty context is forwarded.
- All signals without a GitHub URL are silently dropped by the enrich node.

## Testing

- `telegram_enrich_node`: mock `httpx` — verify URL extraction, README truncation, drop behaviour for non-GitHub signals and failed fetches
- `telegram_analyze_node`: mock `openai` — verify classification uses `readme_excerpt`, no HTTP calls present
