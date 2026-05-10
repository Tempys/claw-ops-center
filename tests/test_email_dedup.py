# tests/test_email_dedup.py
from news.nodes.email_dedup import email_dedup_node


def _sig(title: str, summary: str = "") -> dict:
    url = f"https://mail.example.com/{title.lower().replace(' ', '-')}"
    return {"url": url, "title": title, "classification": "other", "summary": summary, "source": "email"}


STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_passes_new_email_signals_through():
    state = {**STATE_BASE, "email_raw_signals": [_sig("Weekly AI Digest", "lots of content")]}
    result = await email_dedup_node(state)
    assert len(result["email_raw_signals"]) == 1


async def test_drops_already_seen_email():
    from news.nodes.email_dedup import _signal_hash
    signal = _sig("Weekly AI Digest", "lots of content")
    h = _signal_hash(signal)
    state = {**STATE_BASE, "email_raw_signals": [signal], "email_seen_hashes": [h]}
    result = await email_dedup_node(state)
    assert result["email_raw_signals"] == []


async def test_adds_new_email_hashes_to_seen():
    signal = _sig("New newsletter", "content here")
    state = {**STATE_BASE, "email_raw_signals": [signal]}
    result = await email_dedup_node(state)
    assert len(result["email_seen_hashes"]) == 1


async def test_does_not_re_add_existing_hash():
    from news.nodes.email_dedup import _signal_hash
    signal = _sig("Seen before", "content")
    h = _signal_hash(signal)
    state = {**STATE_BASE, "email_raw_signals": [signal], "email_seen_hashes": [h]}
    result = await email_dedup_node(state)
    # node returns only NEW hashes; _list_union reducer merges with existing ones
    assert result["email_seen_hashes"] == []


