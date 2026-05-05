# tests/test_telegram_analyzer.py
from unittest.mock import AsyncMock, MagicMock, patch


def _make_openai_parse_response(cls: str, description: str = "A project", reason: str = "It fits") -> MagicMock:
    """Build a minimal mock that matches resp.choices[0].message.parsed."""
    parsed = MagicMock()
    parsed.classification = cls
    parsed.description = description
    parsed.reason = reason
    message = MagicMock()
    message.parsed = parsed
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


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
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(side_effect=[
        _make_openai_parse_response("ai_agent_framework", "LangGraph agent framework", "Orchestrates LLM agents"),
        _make_openai_parse_response("other"),
    ])

    with (
        patch("news.nodes.telegram_analyzer._client", mock_client),
        patch("news.nodes.telegram_analyzer._fetch_github_readme", AsyncMock(return_value="")),
    ):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    assert len(result["filtered_signals"]) == 1
    assert result["filtered_signals"][0]["classification"] == "ai_agent_framework"


async def test_telegram_analyze_node_returns_empty_when_all_other():
    signals = [
        {"title": "BTC up 5%", "classification": "other", "summary": "Price update", "source": "telegram"},
    ]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(return_value=_make_openai_parse_response("other"))

    with (
        patch("news.nodes.telegram_analyzer._client", mock_client),
        patch("news.nodes.telegram_analyzer._fetch_github_readme", AsyncMock(return_value="")),
    ):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    assert result["filtered_signals"] == []


async def test_telegram_analyze_node_enriches_summary():
    signals = [
        {"title": "Tool X", "classification": "other", "summary": "A new tool", "source": "telegram"},
    ]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_openai_parse_response(
            "dev_productivity",
            "Tool X boosts developer workflow",
            "Directly improves dev productivity",
        )
    )

    with (
        patch("news.nodes.telegram_analyzer._client", mock_client),
        patch("news.nodes.telegram_analyzer._fetch_github_readme", AsyncMock(return_value="")),
    ):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    assert len(result["filtered_signals"]) == 1
    sig = result["filtered_signals"][0]
    assert "Tool X boosts developer workflow" in sig["summary"]
    assert "Directly improves dev productivity" in sig["summary"]


async def test_telegram_analyze_node_fetches_github_context():
    signals = [
        {
            "title": "Check out https://github.com/openai/openai-agents",
            "classification": "other",
            "summary": "Check out https://github.com/openai/openai-agents",
            "source": "telegram",
        }
    ]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_openai_parse_response("ai_agent_framework")
    )
    mock_readme = AsyncMock(return_value="# OpenAI Agents\nA framework for building agents.")

    with (
        patch("news.nodes.telegram_analyzer._client", mock_client),
        patch("news.nodes.telegram_analyzer._fetch_github_readme", mock_readme),
    ):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    mock_readme.assert_awaited_once_with("openai", "openai-agents")
    call_messages = mock_client.beta.chat.completions.parse.call_args.kwargs["messages"]
    user_content = next(m["content"] for m in call_messages if m["role"] == "user")
    assert "GitHub README excerpt" in user_content


async def test_telegram_analyze_node_skips_error_signals():
    signals = [
        {"title": "Bad signal", "classification": "error", "summary": "", "source": "telegram"},
    ]
    mock_client = MagicMock()

    with (
        patch("news.nodes.telegram_analyzer._client", mock_client),
        patch("news.nodes.telegram_analyzer._fetch_github_readme", AsyncMock(return_value="")),
    ):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    mock_client.beta.chat.completions.parse.assert_not_called()
    assert result["filtered_signals"] == []


async def test_telegram_analyze_node_falls_back_on_llm_error():
    signals = [
        {"title": "Some tool", "classification": "other", "summary": "A cool tool", "source": "telegram"},
    ]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API down"))

    with (
        patch("news.nodes.telegram_analyzer._client", mock_client),
        patch("news.nodes.telegram_analyzer._fetch_github_readme", AsyncMock(return_value="")),
    ):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_raw_signals": signals})

    assert result["filtered_signals"] == []
