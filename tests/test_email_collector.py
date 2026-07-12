from news.nodes import email_collector, gmail_client

STATE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 1000.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_returns_empty_when_gmail_unconfigured():
    # No OAuth token exists in the test env -> fetch raises -> graceful [].
    result = await email_collector.email_collector_node(STATE)
    assert result["email_raw_signals"] == []


async def test_builds_signals_from_fetched_emails(monkeypatch):
    sample = [
        {
            "id": "m1",
            "permalink": "https://mail.google.com/mail/u/0/#all/m1",
            "subject": "AutoGen v0.5 released",
            "body": "New multi-agent framework release with tool-use.",
            "snippet": "New multi-agent...",
        }
    ]
    monkeypatch.setattr(gmail_client, "fetch_recent_emails", lambda: sample)
    monkeypatch.setattr(
        email_collector.config, "GMAIL_MARK_PROCESSED", False, raising=False
    )

    result = await email_collector.email_collector_node(STATE)

    assert len(result["email_raw_signals"]) == 1
    sig = result["email_raw_signals"][0]
    assert sig["url"] == sample[0]["permalink"]
    assert sig["title"] == "AutoGen v0.5 released"
    assert sig["source"] == "email"
    assert "multi-agent" in sig["summary"]


async def test_falls_back_to_snippet_when_no_body(monkeypatch):
    sample = [
        {"id": "m1", "permalink": "p1", "subject": "s", "body": "", "snippet": "snip"}
    ]
    monkeypatch.setattr(gmail_client, "fetch_recent_emails", lambda: sample)
    monkeypatch.setattr(
        email_collector.config, "GMAIL_MARK_PROCESSED", False, raising=False
    )

    result = await email_collector.email_collector_node(STATE)
    assert result["email_raw_signals"][0]["summary"] == "snip"


async def test_marks_processed_when_enabled(monkeypatch):
    sample = [
        {"id": "m1", "permalink": "p1", "subject": "s", "body": "b", "snippet": ""}
    ]
    marked: list[str] = []
    monkeypatch.setattr(gmail_client, "fetch_recent_emails", lambda: sample)
    monkeypatch.setattr(gmail_client, "mark_processed", lambda ids: marked.extend(ids))
    monkeypatch.setattr(
        email_collector.config, "GMAIL_MARK_PROCESSED", True, raising=False
    )

    await email_collector.email_collector_node(STATE)
    assert marked == ["m1"]
