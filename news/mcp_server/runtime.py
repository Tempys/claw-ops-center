"""Adapter interface between the MCP server and the OpenClaw Runtime.

The Runtime internals — Topic Registry, Digest Composer, Analysis Engine — are
owned by Epic 1 (OpenClaw Config) and are not implemented yet. This module
defines the ``Runtime`` interface the MCP tools depend on, plus a ``StubRuntime``
whose every operation raises :class:`NotImplementedRuntimeError`.

The MCP server holds a ``Runtime`` instance and is fully wired against this
interface, so swapping ``StubRuntime`` for a real implementation later requires
no change to ``server.py``.
"""

from typing import Protocol, TypedDict, runtime_checkable


class Topic(TypedDict):
    id: str
    name: str


class NotImplementedRuntimeError(RuntimeError):
    """Raised by stub Runtime methods until Epic 1 wires the real internals."""


@runtime_checkable
class Runtime(Protocol):
    """Operations the MCP tools/resources proxy to the OpenClaw Runtime."""

    async def list_topics(self) -> list[Topic]: ...

    async def add_topic(self, name: str) -> Topic: ...

    async def remove_topic(self, topic_id: str) -> bool: ...

    async def get_digest(self) -> str: ...

    async def trigger_analysis(self) -> str: ...

    async def topic_registry_state(self) -> dict: ...


_STUB_MSG = (
    "OpenClaw Runtime internals are not implemented yet (Epic 1: OpenClaw "
    "Config). This MCP endpoint is wired and will work once the Runtime is "
    "available."
)


class StubRuntime:
    """Placeholder Runtime: every operation reports it is not yet implemented."""

    async def list_topics(self) -> list[Topic]:
        raise NotImplementedRuntimeError(_STUB_MSG)

    async def add_topic(self, name: str) -> Topic:
        raise NotImplementedRuntimeError(_STUB_MSG)

    async def remove_topic(self, topic_id: str) -> bool:
        raise NotImplementedRuntimeError(_STUB_MSG)

    async def get_digest(self) -> str:
        raise NotImplementedRuntimeError(_STUB_MSG)

    async def trigger_analysis(self) -> str:
        raise NotImplementedRuntimeError(_STUB_MSG)

    async def topic_registry_state(self) -> dict:
        raise NotImplementedRuntimeError(_STUB_MSG)
