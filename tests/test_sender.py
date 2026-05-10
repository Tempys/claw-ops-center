from unittest.mock import AsyncMock, call, patch

import news.config as config

STATE_WITH_SIGNALS = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [],
    "filtered_signals": [
        {"github_link": "https://github.com/langchain-ai/langgraph", "summary": "LangGraph major release"},
        {"github_link": "https://github.com/microsoft/autogen", "summary": "AutoGen 0.4 released"},
    ],
}

STATE_EMPTY = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [],
    "filtered_signals": [],
}


async def test_sends_each_filtered_signal_as_separate_message():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        result = await sender_node(STATE_WITH_SIGNALS)

    assert mock_bot.send_message.call_count == 2
    mock_bot.send_message.assert_any_call(
        chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
        text="https://github.com/langchain-ai/langgraph\n\nLangGraph major release",
    )
    mock_bot.send_message.assert_any_call(
        chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
        text="https://github.com/microsoft/autogen\n\nAutoGen 0.4 released",
    )
    assert result == {}


async def test_sends_nothing_when_filtered_signals_empty():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        result = await sender_node(STATE_EMPTY)

    mock_bot.send_message.assert_not_called()
    assert result == {}


async def test_returns_empty_dict():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        result = await sender_node(STATE_EMPTY)

    assert result == {}
