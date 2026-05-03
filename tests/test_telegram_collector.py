from unittest.mock import AsyncMock, MagicMock, patch

STATE = {
    "telegram_offset_id": 100,
    "email_last_checked": 0.0,
    "signals": [],
    "analysis": "",
}


async def test_returns_signals_and_updates_offset():
    msg1 = MagicMock(id=200, text="Urgent: BTC liquidations spike", caption=None)
    msg2 = MagicMock(id=150, text="Weekly update published", caption=None)
    mock_client = AsyncMock()
    mock_client.get_chat_history = AsyncMock(return_value=[msg1, msg2])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node
        result = await telegram_collector_node(STATE)

    assert result["telegram_offset_id"] == 200
    assert len(result["signals"]) == 2
    assert result["signals"][0]["source"] == "telegram"
    assert result["signals"][0]["title"] == "Urgent: BTC liquidations spike"


async def test_returns_empty_dict_when_no_messages():
    mock_client = AsyncMock()
    mock_client.get_chat_history = AsyncMock(return_value=[])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node
        result = await telegram_collector_node(STATE)

    assert result == {}


async def test_returns_error_signal_and_preserves_offset_on_exception():
    mock_client = AsyncMock()
    mock_client.get_chat_history = AsyncMock(side_effect=Exception("connection refused"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node
        result = await telegram_collector_node(STATE)

    assert "telegram_offset_id" not in result
    assert len(result["signals"]) == 1
    assert result["signals"][0]["classification"] == "error"
    assert result["signals"][0]["source"] == "telegram"
    assert "connection refused" in result["signals"][0]["summary"]
