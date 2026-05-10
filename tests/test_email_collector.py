STATE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 1000.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_returns_empty_raw_signals():
    from news.nodes.email_collector import email_collector_node

    result = await email_collector_node(STATE)
    assert result["email_raw_signals"] == []


async def test_returns_empty_signals_when_no_emails():
    from news.nodes.email_collector import email_collector_node

    result = await email_collector_node(STATE)
    assert result["email_raw_signals"] == []


async def test_returns_empty_on_any_state():
    from news.nodes.email_collector import email_collector_node

    result = await email_collector_node(STATE)
    assert "email_raw_signals" in result
