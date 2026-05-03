import logging

from pyrogram import Client
from pyrogram.types import Message

import news.config as config
from news.state import Signal, State

log = logging.getLogger(__name__)


def make_client() -> Client:
    return Client(
        "claw_session",
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
        session_string=config.TELEGRAM_SESSION_STRING or None,
    )


def _to_signal(message: Message) -> Signal:
    text = message.text or message.caption or ""
    return Signal(
        title=text[:80],
        classification="other",
        summary=text,
        source="telegram",
    )


async def telegram_collector_node(state: State) -> dict:
    try:
        async with make_client() as client:
            await client.get_chat(config.TELEGRAM_CHANNEL_ID)
            messages = [
                m async for m in client.get_chat_history(
                    config.TELEGRAM_CHANNEL_ID,
                    limit=100,
                    offset_id=state["telegram_offset_id"],
                )
            ]
        # pyrogram returns messages in descending order (newest first); messages[0] has the highest ID
        if not messages:
            return {}
        return {
            "telegram_offset_id": messages[0].id,
            "signals": [_to_signal(m) for m in messages],
        }
    except Exception as exc:
        log.error(f"Telegram collector failed: {exc}", exc_info=True)

        return {
            "signals": [Signal(
                title="Telegram collector failed",
                classification="error",
                summary=str(exc),
                source="telegram",
            )]
        }
