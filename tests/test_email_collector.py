from unittest.mock import patch

STATE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 1000.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
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
    assert len(result["email_raw_signals"]) == 2
    assert result["email_raw_signals"][0]["source"] == "email"
    assert result["email_raw_signals"][0]["title"] == "Market Alert"
    assert result["email_raw_signals"][1]["title"] == "Weekly Digest"


async def test_returns_empty_signals_when_no_emails():
    with patch("news.nodes.email_collector.fetch_emails_since", return_value=[]):
        with patch("news.nodes.email_collector.time") as mock_time:
            mock_time.time.return_value = 9999.0
            from news.nodes.email_collector import email_collector_node
            result = await email_collector_node(STATE)

    assert result["email_last_checked"] == 9999.0
    assert result["email_raw_signals"] == []


async def test_returns_error_signal_and_preserves_timestamp_on_exception():
    with patch("news.nodes.email_collector.fetch_emails_since", side_effect=Exception("IMAP auth failed")):
        from news.nodes.email_collector import email_collector_node
        result = await email_collector_node(STATE)

    assert "email_last_checked" not in result
    assert len(result["email_raw_signals"]) == 1
    assert result["email_raw_signals"][0]["classification"] == "error"
    assert result["email_raw_signals"][0]["source"] == "email"
    assert "IMAP auth failed" in result["email_raw_signals"][0]["summary"]
