import logging

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from openclaw.config import OpenClawConfig
from openclaw.orchestrator import Orchestrator

log = logging.getLogger(__name__)


class TelegramAdapter:
    def __init__(self, config: OpenClawConfig, orchestrator: Orchestrator) -> None:
        self._config = config
        self._orchestrator = orchestrator
        self._app: Application = (
            Application.builder()
            .token(config.telegram.bot_token.get_secret_value())
            .build()
        )
        self._orchestrator.set_reply_callback(self._send_reply)
        self._app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )

    async def _on_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        chat_id = str(update.effective_chat.id)
        text = update.message.text

        if chat_id != self._config.telegram.chat_id:
            log.warning("Ignoring message from unknown chat %s", chat_id)
            return

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)
        await self._orchestrator.handle_message(chat_id, text)

    async def _send_reply(self, chat_id: str, text: str) -> None:
        await self._app.bot.send_message(chat_id=chat_id, text=text)

    def run(self) -> None:
        log.info("OpenClaw polling started")
        self._app.run_polling(allowed_updates=Update.ALL_TYPES)
