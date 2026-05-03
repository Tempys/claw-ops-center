import logging

from telegram import Bot

import news.config as config
from news.state import State

log = logging.getLogger(__name__)

_bot = Bot(token=config.TELEGRAM_BOT_TOKEN)


async def sender_node(state: State) -> dict:
    signals = state["filtered_signals"]
    if not signals:
        log.info("No signals to send")
        return {}
    for signal in signals:
        await _bot.send_message(
            chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
            text=signal["summary"],
        )
        log.info("Sent signal: %s", signal["title"])
    return {}
