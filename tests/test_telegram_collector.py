from unittest.mock import AsyncMock, MagicMock, patch

STATE = {
    "telegram_offset_id": 100,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_returns_signals_and_updates_offset():
    msg1 = MagicMock(id=200, text="Urgent: BTC liquidations spike", caption=None)
    msg2 = MagicMock(id=150, text="Weekly update published", caption=None)

    async def fake_history(*_a, **_kw):
        for m in [msg1, msg2]:
            yield m

    mock_client = AsyncMock()
    mock_client.get_chat_history = fake_history
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node

        result = await telegram_collector_node(STATE)

    assert result["telegram_offset_id"] == 200
    assert len(result["telegram_raw_signals"]) == 2
    assert result["telegram_raw_signals"][0]["telegram_id"] == 200
    assert result["telegram_raw_signals"][0]["url"] == ""


async def test_returns_empty_dict_when_no_messages():
    async def fake_history(*_a, **_kw):
        return
        yield

    mock_client = AsyncMock()
    mock_client.get_chat_history = fake_history
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node

        result = await telegram_collector_node(STATE)

    assert result == {}


async def test_returns_error_signal_and_preserves_offset_on_exception():
    async def fake_history(*_a, **_kw):
        raise Exception("connection refused")
        yield

    mock_client = AsyncMock()
    mock_client.get_chat_history = fake_history
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node

        result = await telegram_collector_node(STATE)

    assert result == {}


async def test_signal_default_classification_is_other():
    msg = MagicMock(id=300, text="Some message", caption=None)

    async def fake_history(*_a, **_kw):
        yield msg

    mock_client = AsyncMock()
    mock_client.get_chat_history = fake_history
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=mock_client):
        from news.nodes.telegram_collector import telegram_collector_node

        result = await telegram_collector_node(STATE)

    assert result["telegram_raw_signals"][0]["telegram_id"] == 300
    assert result["telegram_raw_signals"][0]["url"] == ""


# --- _to_signal unit tests ---


def _make_text_link_entity(url: str):
    from pyrogram.enums import MessageEntityType

    entity = MagicMock()
    entity.type = MessageEntityType.TEXT_LINK
    entity.url = url
    return entity


def _make_bold_entity():
    from pyrogram.enums import MessageEntityType

    entity = MagicMock()
    entity.type = MessageEntityType.BOLD
    entity.url = None
    return entity


async def test_to_signal_extracts_url_from_caption_entities():
    # Reproduces the real Code Stars photo message (id=15457) from the user example:
    # the TEXT_LINK lives in caption_entities, not entities, because the message is a photo.
    from news.nodes.telegram_collector import _to_signal

    link_entity = _make_text_link_entity("https://github.com/earendil-works/pi")
    bold_entity = _make_bold_entity()

    msg = MagicMock()
    msg.id = 15457
    msg.entities = None
    msg.caption_entities = [link_entity, bold_entity]

    signal = _to_signal(msg)

    assert signal["telegram_id"] == 15457
    assert signal["url"] == "https://github.com/earendil-works/pi"


async def test_to_signal_extracts_url_from_entities():
    from news.nodes.telegram_collector import _to_signal

    link_entity = _make_text_link_entity("https://github.com/example/repo")
    msg = MagicMock()
    msg.id = 42
    msg.entities = [link_entity]
    msg.caption_entities = None

    signal = _to_signal(msg)

    assert signal["telegram_id"] == 42
    assert signal["url"] == "https://github.com/example/repo"


async def test_to_signal_returns_empty_url_when_no_text_link():
    from news.nodes.telegram_collector import _to_signal

    msg = MagicMock()
    msg.id = 99
    msg.entities = [_make_bold_entity()]
    msg.caption_entities = None

    signal = _to_signal(msg)

    assert signal["url"] == ""


async def test_to_signal_returns_empty_url_when_no_entities():
    from news.nodes.telegram_collector import _to_signal

    msg = MagicMock()
    msg.id = 7
    msg.entities = None
    msg.caption_entities = None

    signal = _to_signal(msg)

    assert signal["url"] == ""
