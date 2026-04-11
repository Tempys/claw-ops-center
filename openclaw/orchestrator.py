import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

from anthropic import AsyncAnthropic
from openclaw.config import OpenClawConfig

log = logging.getLogger(__name__)
MAX_HISTORY_TURNS = 20


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Session:
    chat_id: str
    history: list[Message] = field(default_factory=list)
    queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    worker_task: asyncio.Task | None = None

    def bounded_history(self) -> list[Message]:
        return self.history[-(MAX_HISTORY_TURNS * 2):]


def _extract_text(msg) -> str:
    return "".join(block.text for block in msg.content if block.type == "text")


class Orchestrator:
    def __init__(self, config: OpenClawConfig) -> None:
        self._config = config
        self._client = AsyncAnthropic(
            api_key=config.anthropic_api_key.get_secret_value()
        )
        self._sessions: dict[str, Session] = {}
        self._system_prompt = self._build_system_prompt()
        self._on_reply: Callable[[str, str], Awaitable[None]] | None = None

    def set_reply_callback(self, cb: Callable[[str, str], Awaitable[None]]) -> None:
        self._on_reply = cb

    def _build_system_prompt(self) -> str:
        parts = [
            "You are a personal AI assistant running inside OpenClaw.",
            "Be concise and direct.",
        ]
        if self._config.topics:
            parts.append(f"You are particularly focused on: {', '.join(self._config.topics)}.")
        return "\n".join(parts)

    def _get_or_create_session(self, chat_id: str) -> Session:
        if chat_id not in self._sessions:
            self._sessions[chat_id] = Session(chat_id=chat_id)
        return self._sessions[chat_id]

    async def handle_message(self, chat_id: str, text: str) -> None:
        session = self._get_or_create_session(chat_id)
        await session.queue.put(text)
        if session.worker_task is None or session.worker_task.done():
            session.worker_task = asyncio.create_task(self._drain_queue(session))

    async def _drain_queue(self, session: Session) -> None:
        while True:
            try:
                text = session.queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                reply = await self._run_react_loop(session, text)
                session.history.append(Message(role="assistant", content=reply))
                if self._on_reply:
                    await self._on_reply(session.chat_id, reply)
            except Exception:
                log.exception("Error processing message for chat %s", session.chat_id)
            finally:
                session.queue.task_done()

    async def _run_react_loop(self, session: Session, user_text: str) -> str:
        session.history.append(Message(role="user", content=user_text))
        messages = self._assemble_context(session)

        for _ in range(10):
            async with self._client.messages.stream(
                model="claude-opus-4-5",
                max_tokens=4096,
                system=self._system_prompt,
                messages=messages,
                tools=[],
            ) as stream:
                final_msg = await stream.get_final_message()

            if final_msg.stop_reason == "end_turn":
                return _extract_text(final_msg)

            if final_msg.stop_reason == "tool_use":
                tool_results = await self._dispatch_tools(final_msg)
                messages.append({"role": "assistant", "content": final_msg.content})
                messages.append({"role": "user", "content": tool_results})
                continue

            return _extract_text(final_msg)

        return "[Max iterations reached]"

    async def _dispatch_tools(self, msg) -> list[dict]:
        return [
            {"type": "tool_result", "tool_use_id": b.id, "content": "Tool not implemented"}
            for b in msg.content if b.type == "tool_use"
        ]

    def _assemble_context(self, session: Session) -> list[dict]:
        return [
            {"role": m.role, "content": m.content}
            for m in session.bounded_history()
        ]
