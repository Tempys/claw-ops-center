from pyrogram import Client

import openclaw.config as config
from openclaw.state import Signal, State


def make_client() -> Client:
    return Client(
        "claw_session",
        api_id=config.TELEGRAM_API_ID,
        api_hash=config.TELEGRAM_API_HASH,
    )


def _to_signal(message) -> Signal:
    text = message.text or message.caption or ""
    return Signal(
        title=text[:80],
        classification="informational",
        summary=text,
        source="telegram",
    )


async def telegram_collector_node(state: State) -> dict:
    try:
        async with make_client() as client:
            messages = await client.get_chat_history(
                config.TELEGRAM_CHANNEL_ID,
                limit=100,
                offset_id=state["telegram_offset_id"],
            )
        if not messages:
            return {}
        return {
            "telegram_offset_id": messages[0].id,
            "signals": [_to_signal(m) for m in messages],
        }
    except Exception as exc:
        return {
            "signals": [Signal(
                title="Telegram collector failed",
                classification="error",
                summary=str(exc),
                source="telegram",
            )]
        }
