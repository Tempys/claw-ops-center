# Per-Message Classify and Send Design

**Date:** 2026-05-03
**Scope:** `news/state.py`, `news/nodes/analyzer.py`, `news/nodes/sender.py`, `news/graph.py`

## Goal

Replace the batch-digest pipeline with a per-message flow: classify each collected signal individually, forward only dev-tool related ones as raw text to the Telegram channel, and silently drop everything else.

## State Changes

`news/state.py`:

- Remove `analysis: str` — no digest is produced
- Add `filtered_signals: list[Signal]` — plain field (no reducer), written once by `classify_and_filter_node`, read by `sender_node`

```python
class State(TypedDict):
    telegram_offset_id: int
    email_last_checked: float
    signals: Annotated[list[Signal], operator.add]
    filtered_signals: list[Signal]
```

## Node: classify_and_filter_node

Replaces `analyze_and_classify_node` in `news/nodes/analyzer.py`.

- `_classify_batch` helper is unchanged
- `_DIGEST_SYSTEM` prompt and digest LLM call are removed entirely
- Top-level node classifies all signals in batches of 5, then filters to dev-tool only:

```python
async def classify_and_filter_node(state: State) -> dict:
    signals = state["signals"]
    classified: list[Signal] = []
    for i in range(0, len(signals), 5):
        classified.extend(await _classify_batch(signals[i : i + 5]))
    dev_tool = [s for s in classified if s["classification"] not in {"other", "error"}]
    return {"filtered_signals": dev_tool}
```

Signals classified as `"other"` or `"error"` are silently dropped.

## Node: sender_node

`news/nodes/sender.py` — iterates `filtered_signals`, sends each signal's `summary` as a separate Telegram message. Sends nothing if the list is empty.

```python
async def sender_node(state: State) -> dict:
    for signal in state["filtered_signals"]:
        await _bot.send_message(
            chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
            text=signal["summary"],
        )
    return {}
```

## Graph

`news/graph.py` — replaces `analyze_and_classify` node with `classify_and_filter`:

```
START → telegram_collector → classify_and_filter → sender → END
```

## Error Handling

- If `_classify_batch` fails for a batch, all signals in that batch fall back to `"other"` and are dropped. Pipeline never crashes.
- If `filtered_signals` is empty (no dev-tool signals found), `sender_node` sends nothing.

## Runner Initial State

`news/runner.py` — update `_INITIAL_STATE` to remove `analysis` and add `filtered_signals`:

```python
_INITIAL_STATE: State = {
    "telegram_offset_id": 0,
    "email_last_checked": time.time(),
    "signals": [],
    "filtered_signals": [],
}
```

## Out of Scope

- Rate limiting between Telegram sends
- Message deduplication
- Email collector (remains disabled)
