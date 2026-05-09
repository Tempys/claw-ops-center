import logging

from telegram import Bot
from telegram.request import HTTPXRequest

import news.config as config
from news.state import State  # outer graph state

log = logging.getLogger(__name__)

_bot = Bot(token=config.TELEGRAM_BOT_TOKEN, request=HTTPXRequest(read_timeout=30))


async def sender_node(state: State) -> dict:
    signals = state["filtered_signals"]
    if not signals:
        log.info("No signals to send")
        return {}
    for signal in signals:
        text = f"{signal['github_link']}\n\n{signal['summary']}"
        await _bot.send_message(
            chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
            text=text,
        )
        log.info("Sent: %s", signal["github_link"])
    return {}
