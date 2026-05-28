import base64

import news.config as config
from news.nodes import gmail_client


def _b64(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode()).decode().rstrip("=")


def test_split_trims_and_drops_empties():
    assert gmail_client._split("a@b.com, news@x.io ,") == ["a@b.com", "news@x.io"]
    assert gmail_client._split("") == []


def test_build_query_combines_filters(monkeypatch):
    monkeypatch.setattr(config, "GMAIL_SENDERS", "a@b.com,news@x.io", raising=False)
    monkeypatch.setattr(config, "GMAIL_LABELS", "INBOX", raising=False)
    monkeypatch.setattr(config, "GMAIL_SUBJECT_FILTER", "", raising=False)
    monkeypatch.setattr(config, "GMAIL_QUERY", "", raising=False)
    monkeypatch.setattr(config, "GMAIL_LOOKBACK", "7d", raising=False)
    monkeypatch.setattr(config, "GMAIL_MARK_PROCESSED", False, raising=False)

    q = gmail_client._build_query()
    assert "from:a@b.com OR from:news@x.io" in q
    assert "label:INBOX" in q
    assert "newer_than:7d" in q


def test_build_query_excludes_processed_label_when_marking(monkeypatch):
    for name in (
        "GMAIL_SENDERS",
        "GMAIL_LABELS",
        "GMAIL_SUBJECT_FILTER",
        "GMAIL_QUERY",
    ):
        monkeypatch.setattr(config, name, "", raising=False)
    monkeypatch.setattr(config, "GMAIL_LOOKBACK", "", raising=False)
    monkeypatch.setattr(config, "GMAIL_MARK_PROCESSED", True, raising=False)
    monkeypatch.setattr(
        config, "GMAIL_PROCESSED_LABEL", "OpenClawProcessed", raising=False
    )

    assert "-label:OpenClawProcessed" in gmail_client._build_query()


def test_decode_handles_missing_padding():
    assert gmail_client._decode(_b64("hello world")) == "hello world"


def test_html_to_text_strips_tags_scripts_and_unescapes():
    html = "<body><p>Hello&nbsp;<b>World</b></p><script>evil()</script></body>"
    text = gmail_client._html_to_text(html)
    assert "Hello" in text
    assert "World" in text
    assert "evil" not in text
    assert "<" not in text


def test_extract_body_prefers_plain_over_html():
    payload = {
        "mimeType": "multipart/alternative",
        "parts": [
            {"mimeType": "text/plain", "body": {"data": _b64("plain version")}},
            {"mimeType": "text/html", "body": {"data": _b64("<p>html version</p>")}},
        ],
    }
    assert gmail_client._extract_body(payload) == "plain version"


def test_extract_body_falls_back_to_html():
    payload = {
        "mimeType": "text/html",
        "body": {"data": _b64("<p>only <b>html</b></p>")},
    }
    assert gmail_client._extract_body(payload) == "only html"


def test_parse_message_extracts_fields():
    msg = {
        "id": "m1",
        "threadId": "t1",
        "snippet": "snippet text",
        "labelIds": ["INBOX"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                {"name": "Subject", "value": "AutoGen v0.5"},
                {"name": "From", "value": "news@example.com"},
            ],
            "body": {"data": _b64("body content")},
        },
    }
    parsed = gmail_client._parse_message(msg)
    assert parsed["id"] == "m1"
    assert parsed["subject"] == "AutoGen v0.5"
    assert parsed["sender"] == "news@example.com"
    assert parsed["body"] == "body content"
    assert parsed["permalink"].endswith("m1")
