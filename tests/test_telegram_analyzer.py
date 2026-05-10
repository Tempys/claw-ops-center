# tests/test_telegram_analyzer.py
from unittest.mock import AsyncMock, MagicMock, patch


def _make_parse_response(cls: str, description: str = "A project", reason: str = "It fits") -> MagicMock:
    parsed = MagicMock()
    parsed.classification = cls
    parsed.description = description
    parsed.reason = reason
    parsed.summary = f"{description} — {reason}".removesuffix(" —")
    message = MagicMock()
    message.parsed = parsed
    choice = MagicMock()
    choice.message = message
    resp = MagicMock()
    resp.choices = [choice]
    return resp


def _enriched(title: str, readme: str = "# Some README") -> dict:
    return {
        "title": title,
        "source": "telegram",
        "github_link": "https://github.com/some-owner/some-repo",
        "readme": readme,
    }


STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "telegram_enriched_signals": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_analyze_node_classifies_enriched_signals():
    signals = [
        _enriched("LangGraph 2.0 drops"),
        _enriched("BTC up 5%"),
    ]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(side_effect=[
        _make_parse_response("ai_agent_framework", "LangGraph agent framework", "Orchestrates LLM agents"),
        _make_parse_response("other"),
    ])

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    assert len(result["filtered_signals"]) == 1
    sig = result["filtered_signals"][0]
    assert sig["github_link"] == "https://github.com/some-owner/some-repo"
    assert "LangGraph agent framework" in sig["summary"]


async def test_analyze_node_returns_empty_when_all_other():
    signals = [_enriched("BTC up 5%")]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(return_value=_make_parse_response("other"))

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    assert result["filtered_signals"] == []


async def test_analyze_node_passes_enriched_signal_through():
    signals = [_enriched("Tool X", readme="# Tool X docs")]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_parse_response("dev_productivity")
    )

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    assert len(result["filtered_signals"]) == 1
    sig = result["filtered_signals"][0]
    assert sig["github_link"] == "https://github.com/some-owner/some-repo"
    assert sig["summary"] == "A project — It fits"


async def test_analyze_node_includes_readme_in_prompt():
    signals = [_enriched("Tool X", readme="# Tool X\nBoosts productivity dramatically.")]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(
        return_value=_make_parse_response("dev_productivity")
    )

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    call_messages = mock_client.beta.chat.completions.parse.call_args.kwargs["messages"]
    user_content = next(m["content"] for m in call_messages if m["role"] == "user")
    assert "GitHub README excerpt" in user_content
    assert "Boosts productivity dramatically" in user_content


async def test_analyze_node_falls_back_on_llm_error():
    signals = [_enriched("Some tool")]
    mock_client = MagicMock()
    mock_client.beta.chat.completions.parse = AsyncMock(side_effect=Exception("API down"))

    with patch("news.nodes.telegram_analyzer._client", mock_client):
        from news.nodes.telegram_analyzer import telegram_analyze_node
        result = await telegram_analyze_node({**STATE_BASE, "telegram_enriched_signals": signals})

    assert result["filtered_signals"] == []
