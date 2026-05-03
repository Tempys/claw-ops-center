from unittest.mock import AsyncMock, patch

STATE = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [],
    "analysis": "URGENT: BTC up 15%. VIX spike detected.",
}


async def test_sends_analysis_to_destination_chat():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        import news.config as config
        result = await sender_node(STATE)

    mock_bot.send_message.assert_called_once_with(
        chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
        text="URGENT: BTC up 15%. VIX spike detected.",
    )
    assert result == {}


async def test_returns_empty_dict():
    mock_bot = AsyncMock()
    mock_bot.send_message = AsyncMock()

    with patch("news.nodes.sender._bot", mock_bot):
        from news.nodes.sender import sender_node
        result = await sender_node(STATE)

    assert result == {}
