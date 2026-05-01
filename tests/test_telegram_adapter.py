import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.messages import AIMessage

from openclaw.telegram_adapter import TelegramAdapter


def _make_adapter(chat_id: str = "12345") -> TelegramAdapter:
    """Build a TelegramAdapter instance without calling __init__."""
    adapter = object.__new__(TelegramAdapter)
    config = MagicMock()
    config.telegram.chat_id = chat_id
    adapter._config = config
    adapter._graph = MagicMock()
    adapter._locks = {}
    return adapter


def _make_update(chat_id: str | int, text: str = "hello") -> MagicMock:
    update = MagicMock()
    update.effective_chat.id = chat_id
    update.message.text = text
    return update


def _make_context() -> MagicMock:
    context = MagicMock()
    context.bot.send_chat_action = AsyncMock()
    context.bot.send_message = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_auth_guard_rejects_unknown_chat():
    adapter = _make_adapter(chat_id="12345")
    update = _make_update(chat_id="99999")
    context = _make_context()

    await adapter._on_message(update, context)

    context.bot.send_message.assert_not_called()


@pytest.mark.asyncio
async def test_content_normalization_list_blocks():
    adapter = _make_adapter(chat_id="12345")
    update = _make_update(chat_id="12345", text="hi")
    context = _make_context()

    ai_msg = AIMessage(content=[{"type": "text", "text": "Hello"}, {"type": "text", "text": "world"}])
    adapter._graph.ainvoke = AsyncMock(return_value={"messages": [ai_msg]})

    await adapter._on_message(update, context)

    context.bot.send_message.assert_awaited_once()
    _, kwargs = context.bot.send_message.call_args
    assert kwargs["text"] == "Hello world"


@pytest.mark.asyncio
async def test_reply_truncated_at_4096():
    adapter = _make_adapter(chat_id="12345")
    update = _make_update(chat_id="12345", text="hi")
    context = _make_context()

    ai_msg = AIMessage(content="x" * 5000)
    adapter._graph.ainvoke = AsyncMock(return_value={"messages": [ai_msg]})

    await adapter._on_message(update, context)

    _, kwargs = context.bot.send_message.call_args
    reply = kwargs["text"]
    assert len(reply) <= 4096
    assert reply.endswith("[…]")
