import logging

from telegram import Bot

import news.config as config
from news.state import State

log = logging.getLogger(__name__)

_bot = Bot(token=config.TELEGRAM_BOT_TOKEN)


async def sender_node(state: State) -> dict:
    await _bot.send_message(
        chat_id=config.TELEGRAM_DESTINATION_CHAT_ID,
        text=state["analysis"],
    )
    return {}
