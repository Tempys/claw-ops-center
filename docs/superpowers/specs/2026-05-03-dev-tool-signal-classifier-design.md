# Dev-Tool Signal Classifier Design

**Date:** 2026-05-03
**Scope:** `news/state.py`, `news/nodes/analyzer.py`, `news/nodes/telegram_collector.py`

## Goal

Enhance the analyzer to recognize when Telegram/email signals mention GitHub repos or content related to developer tooling, and classify them into specific dev-tool categories rather than the existing coarse `urgent/informational/noise` taxonomy.

## Data Model

### `state.py`

Add a `Literal` type alias for valid classification values:

```python
CLASSIFICATION = Literal[
    "ai_agent_framework",    # LangGraph, AutoGen, CrewAI, etc.
    "llm_finetuning",        # fine-tuning, autotraining tools
    "skill_plugin_builder",  # Claude/GPT skill and plugin builders
    "code_generation",       # code-gen tools and libraries
    "dev_productivity",      # CLIs, IDE extensions, developer workflow tools
    "prompt_engineering",    # prompt libraries and frameworks
    "other",                 # non-dev-tool content
    "error",                 # reserved for collector failures
]
```

`Signal.classification` is re-typed from `str` to `CLASSIFICATION` so the type checker enforces valid values.

### `telegram_collector.py`

`_to_signal` default classification changes from `"informational"` to `"other"`. This is a placeholder; the analyzer overwrites it.

## Analyzer — Two-Pass Flow

`analyze_and_classify_node` runs two sequential LLM calls per batch of 5 signals.

### Pass 1 — Classify

**System prompt:**
> You are a signal classifier. Given a numbered list of signals, return ONLY a JSON array — no prose, no markdown. Each element: `{"index": <int>, "classification": <category>}`. Valid categories: ai_agent_framework, llm_finetuning, skill_plugin_builder, code_generation, dev_productivity, prompt_engineering, other, error.

- Input: the formatted signal batch (same format as today)
- Output: JSON array parsed into `{index → classification}` mapping
- Signals already classified as `"error"` (collector failures) are passed through unchanged and skipped by the classifier

### Pass 2 — Digest

Uses the existing `_SYSTEM` prompt, unchanged. Signals are re-formatted with their updated classifications. The digest prompt instructs the model to lead with dev-tool category signals before `"other"`.

### Return value

```python
{"signals": <updated_list>, "analysis": <digest_text>}
```

Both fields are returned in a single dict so LangGraph merges them into `State`.

## Error Handling

- If Pass 1 response is not valid JSON or cannot be parsed: fall back to `"other"` for all signals in that batch. Pipeline never crashes.
- If a returned classification value is not in the allowed set: coerce to `"other"`.
- Signals with `classification == "error"` bypass Pass 1 entirely and are included as-is in Pass 2.

## Files Changed

| File | Change |
|------|--------|
| `news/state.py` | Add `CLASSIFICATION` Literal; update `Signal` docstring |
| `news/nodes/telegram_collector.py` | Default classification `"informational"` → `"other"` |
| `news/nodes/analyzer.py` | Two-pass flow: classify then digest; updated system prompts |

## Out of Scope

- GitHub collector node (separate initiative)
- Email collector (currently disabled in graph)
- Routing or filtering signals by category in downstream nodes
