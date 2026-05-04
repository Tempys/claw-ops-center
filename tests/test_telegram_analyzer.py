# tests/test_telegram_analyzer.py
import json
from unittest.mock import AsyncMock, MagicMock, patch


def _make_openai_response(text: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    return response


STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_telegram_analyze_node_returns_filtered_signals():
    signals = [
        {"title": "LangGraph 2.0 drops", "classification": "other", "summary": "Major LangGraph release", "source": "telegram"},
        {"title": "BTC up 5%", "classification": "other", "summary": "Price update", "source": "telegram"},
    ]
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_make_openai_response(classify_json))

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    assert len(result["filtered_signals"]) == 1
    assert result["filtered_signals"][0]["classification"] == "ai_agent_framework"


async def test_telegram_analyze_node_returns_empty_when_all_other():
    signals = [
        {"title": "BTC up 5%", "classification": "other", "summary": "Price update", "source": "telegram"},
    ]
    classify_json = json.dumps([{"index": 1, "classification": "other"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_make_openai_response(classify_json))

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    assert result["filtered_signals"] == []


async def test_telegram_analyze_node_uses_telegram_system_prompt():
    signals = [
        {"title": "Tool X", "classification": "other", "summary": "A new tool", "source": "telegram"},
    ]
    classify_json = json.dumps([{"index": 1, "classification": "dev_productivity"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_make_openai_response(classify_json))

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node, _TELEGRAM_SYSTEM
        await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    call_args = mock_client.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert system_msg == _TELEGRAM_SYSTEM
