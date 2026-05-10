# tests/test_telegram_extractor.py
from unittest.mock import AsyncMock, patch

_RAW_SIGNAL = {
    "telegram_id": 42,
    "url": "https://github.com/openai/openai-agents",
}

_PLAIN_SIGNAL = {
    "telegram_id": 99,
    "url": "",
}

STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "telegram_enriched_signals": [],
    "telegram_id": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_extract_node_extracts_github_url_and_fetches_readme():
    readme = "# OpenAI Agents SDK\nBuild agents with Python."
    with patch("news.nodes.telegram_extractor._fetch_readme", AsyncMock(return_value=readme)):
        from news.nodes.telegram_extractor import telegram_extract_node
        result = await telegram_extract_node({**STATE_BASE, "telegram_raw_signals": [_RAW_SIGNAL]})

    assert len(result["telegram_enriched_signals"]) == 1
    sig = result["telegram_enriched_signals"][0]
    assert sig["github_link"] == "https://github.com/openai/openai-agents"
    assert sig["readme"] == readme


async def test_extract_node_drops_plain_text_signals():
    with patch("news.nodes.telegram_extractor._fetch_readme", AsyncMock(return_value="readme")):
        from news.nodes.telegram_extractor import telegram_extract_node
        result = await telegram_extract_node({**STATE_BASE, "telegram_raw_signals": [_PLAIN_SIGNAL]})

    assert result["telegram_enriched_signals"] == []


async def test_extract_node_drops_signal_when_readme_fetch_fails():
    with patch("news.nodes.telegram_extractor._fetch_readme", AsyncMock(return_value="")):
        from news.nodes.telegram_extractor import telegram_extract_node
        result = await telegram_extract_node({**STATE_BASE, "telegram_raw_signals": [_RAW_SIGNAL]})

    assert result["telegram_enriched_signals"] == []


async def test_extract_node_strips_trailing_punctuation_from_repo_name():
    signal = {**_RAW_SIGNAL, "url": "https://github.com/openai/openai-agents."}
    with patch("news.nodes.telegram_extractor._fetch_readme", AsyncMock(return_value="# Agents")) as mock_fetch:
        from news.nodes.telegram_extractor import telegram_extract_node
        await telegram_extract_node({**STATE_BASE, "telegram_raw_signals": [signal]})

    mock_fetch.assert_awaited_once_with("openai", "openai-agents")


async def test_extract_node_passes_correct_fields():
    readme = "# Readme content"
    with patch("news.nodes.telegram_extractor._fetch_readme", AsyncMock(return_value=readme)):
        from news.nodes.telegram_extractor import telegram_extract_node
        result = await telegram_extract_node({**STATE_BASE, "telegram_raw_signals": [_RAW_SIGNAL]})

    sig = result["telegram_enriched_signals"][0]
    assert sig["github_link"] == "https://github.com/openai/openai-agents"
    assert sig["readme"] == readme


async def test_extract_node_drops_signal_with_comma_terminated_url():
    signal = {**_RAW_SIGNAL, "url": "https://github.com/openai/openai-agents,"}
    with patch("news.nodes.telegram_extractor._fetch_readme", AsyncMock(return_value="# README")) as mock_fetch:
        from news.nodes.telegram_extractor import telegram_extract_node
        await telegram_extract_node({**STATE_BASE, "telegram_raw_signals": [signal]})

    mock_fetch.assert_awaited_once_with("openai", "openai-agents")


async def test_extract_node_truncates_readme_to_1500_chars():
    long_readme = "x" * 2000
    with patch("news.nodes.telegram_extractor._fetch_readme", AsyncMock(return_value=long_readme[:1500])):
        from news.nodes.telegram_extractor import telegram_extract_node
        result = await telegram_extract_node({**STATE_BASE, "telegram_raw_signals": [_RAW_SIGNAL]})

    assert len(result["telegram_enriched_signals"][0]["readme"]) == 1500
