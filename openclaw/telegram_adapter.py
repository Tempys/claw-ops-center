import logging

from langchain_core.messages import HumanMessage
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from openclaw.config import OpenClawConfig

log = logging.getLogger(__name__)


class TelegramAdapter:
    def __init__(self, config: OpenClawConfig, graph) -> None:
        self._config = config
        self._graph = graph
        self._app: Application = (
            Application.builder()
            .token(config.telegram.bot_token.get_secret_value())
            .build()
        )
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

        result = await self._graph.ainvoke(
            {"messages": [HumanMessage(content=text)]},
            config={"configurable": {"thread_id": chat_id}},
        )
        reply = result["messages"][-1].content
        await context.bot.send_message(chat_id=chat_id, text=reply)

    def run(self) -> None:
        log.info("OpenClaw polling started")
        self._app.run_polling(allowed_updates=Update.ALL_TYPES)
