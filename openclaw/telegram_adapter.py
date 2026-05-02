import asyncio
import logging

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph.state import CompiledStateGraph
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from openclaw.config import OpenClawConfig

log = logging.getLogger(__name__)


class TelegramAdapter:
    def __init__(self, config: OpenClawConfig, graph: CompiledStateGraph) -> None:
        self._config = config
        self._graph = graph
        self._locks: dict[str, asyncio.Lock] = {}
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
        if not update.effective_chat or not update.message or not update.message.text:
            return

        chat_id = str(update.effective_chat.id)
        text = update.message.text

        if chat_id != self._config.telegram.chat_id:
            log.warning("Ignoring message from unknown chat %s", chat_id)
            return

        await context.bot.send_chat_action(chat_id=chat_id, action=ChatAction.TYPING)

        lock = self._locks.setdefault(chat_id, asyncio.Lock())
        async with lock:
            try:
                result = await self._graph.ainvoke(
                    {"messages": [HumanMessage(content=text)]},
                    config={"configurable": {"thread_id": chat_id}},
                )
                last = result["messages"][-1]
                if isinstance(last, AIMessage) and isinstance(last.content, list):
                    reply = " ".join(
                        block["text"]
                        for block in last.content
                        if block.get("type") == "text"
                    )
                else:
                    reply = str(last.content)
            except Exception:
                log.exception("Graph invocation failed for chat %s", chat_id)
                reply = "Sorry, something went wrong. Please try again."

        if len(reply) > 4096:
            reply = reply[:4090] + "\n[…]"

        await context.bot.send_message(chat_id=chat_id, text=reply)

    def run(self) -> None:
        log.info("OpenClaw polling started")
        self._app.run_polling(allowed_updates=Update.ALL_TYPES)

    async def run_async(self) -> None:
        log.info("OpenClaw polling started")
        async with self._app:
            await self._app.start()
            await self._app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            try:
                await asyncio.Event().wait()
            finally:
                await self._app.updater.stop()
                await self._app.stop()
