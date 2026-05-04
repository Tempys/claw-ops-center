# tests/test_telegram_dedup.py
import pytest
from news.nodes.telegram_dedup import telegram_dedup_node


def _sig(title: str, summary: str = "") -> dict:
    return {"title": title, "classification": "other", "summary": summary, "source": "telegram"}


STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_passes_new_signals_through():
    state = {**STATE_BASE, "telegram_raw_signals": [_sig("LangGraph 2.0", "Major release")]}
    result = await telegram_dedup_node(state)
    assert len(result["telegram_raw_signals"]) == 1
    assert result["telegram_raw_signals"][0]["title"] == "LangGraph 2.0"


async def test_drops_already_seen_signal():
    from news.nodes.telegram_dedup import _signal_hash
    signal = _sig("LangGraph 2.0", "Major release")
    h = _signal_hash(signal)
    state = {**STATE_BASE, "telegram_raw_signals": [signal], "telegram_seen_hashes": [h]}
    result = await telegram_dedup_node(state)
    assert result["telegram_raw_signals"] == []


async def test_adds_new_hashes_to_seen():
    signal = _sig("New framework", "content")
    state = {**STATE_BASE, "telegram_raw_signals": [signal]}
    result = await telegram_dedup_node(state)
    assert len(result["telegram_seen_hashes"]) == 1


async def test_does_not_re_add_existing_hash():
    from news.nodes.telegram_dedup import _signal_hash
    signal = _sig("Seen before", "content")
    h = _signal_hash(signal)
    state = {**STATE_BASE, "telegram_raw_signals": [signal], "telegram_seen_hashes": [h]}
    result = await telegram_dedup_node(state)
    # node returns only NEW hashes; the _list_union reducer merges them with existing ones.
    # a duplicate signal produces no new hashes, so the returned list is empty.
    assert result["telegram_seen_hashes"] == []


async def test_passes_error_signals_through_without_hashing():
    error_sig = {"title": "err", "classification": "error", "summary": "fail", "source": "telegram"}
    state = {**STATE_BASE, "telegram_raw_signals": [error_sig]}
    result = await telegram_dedup_node(state)
    assert len(result["telegram_raw_signals"]) == 1
    assert result["telegram_seen_hashes"] == []
