import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime

from openai import AsyncOpenAI
from openclaw.auth import get_access_token
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


class Orchestrator:
    def __init__(self, config: OpenClawConfig) -> None:
        self._config = config
        self._sessions: dict[str, Session] = {}
        self._system_prompt = self._build_system_prompt()
        self._on_reply: Callable[[str, str], Awaitable[None]] | None = None
        self._cached_token: str | None = None
        self._client: AsyncOpenAI | None = None

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

    async def _get_client(self) -> AsyncOpenAI:
        token = await asyncio.to_thread(get_access_token)
        if token != self._cached_token:
            self._cached_token = token
            self._client = AsyncOpenAI(api_key=token)
        return self._client

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
                reply = await self._call_llm(session, text)
                session.history.append(Message(role="assistant", content=reply))
                if self._on_reply:
                    await self._on_reply(session.chat_id, reply)
            except Exception:
                log.exception("Error processing message for chat %s", session.chat_id)
            finally:
                session.queue.task_done()

    async def _call_llm(self, session: Session, user_text: str) -> str:
        session.history.append(Message(role="user", content=user_text))
        messages = self._assemble_context(session)
        client = await self._get_client()

        response = await client.responses.create(
            model="codex-mini-latest",
            instructions=self._system_prompt,
            input=messages,
        )
        return response.output_text

    def _assemble_context(self, session: Session) -> list[dict]:
        return [
            {"role": m.role, "content": m.content}
            for m in session.bounded_history()
        ]
