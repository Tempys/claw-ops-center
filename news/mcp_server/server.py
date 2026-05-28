"""FastMCP server exposing the OpenClaw Runtime to MCP clients (Claude Code, Codex).

Transport: stdio (the default) — the client launches this as a subprocess, which
keeps the server single-user by construction (no network surface). Every tool
proxies to the module-global ``runtime`` adapter; with the default
``StubRuntime`` each call returns a graceful "not implemented yet" result so a
client can connect and invoke all tools without crashing (Epic 1 wires the real
Runtime later by replacing ``runtime``).
"""

import logging
from collections.abc import Awaitable
from typing import Any

from news.mcp_server.runtime import NotImplementedRuntimeError, Runtime, StubRuntime

try:
    from mcp.server.fastmcp import FastMCP
except ModuleNotFoundError as exc:  # pragma: no cover
    raise ModuleNotFoundError(
        "The MCP SDK is required. Install it with `uv sync` (adds 'mcp')."
    ) from exc

log = logging.getLogger(__name__)

mcp = FastMCP("openclaw")

# Swap this for a real implementation once the OpenClaw Runtime (Epic 1) exists.
runtime: Runtime = StubRuntime()


async def _safe(label: str, coro: Awaitable[Any]) -> Any:
    """Await a Runtime call, converting failures into structured results.

    Keeps the server responsive: a not-yet-implemented or failing Runtime call
    returns a status dict instead of propagating an exception to the client.
    """
    try:
        return await coro
    except NotImplementedRuntimeError as exc:
        return {"status": "not_implemented", "message": str(exc)}
    except Exception as exc:  # noqa: BLE001 - tools must not crash the server
        log.exception("MCP tool %s failed", label)
        return {"status": "error", "message": str(exc)}


# ── tools ────────────────────────────────────────────────────────────────────


@mcp.tool()
async def list_topics() -> Any:
    """List every topic tracked in the OpenClaw Topic Registry."""
    return await _safe("list_topics", runtime.list_topics())


@mcp.tool()
async def add_topic(name: str) -> Any:
    """Add a topic to track. `name` is the human-readable topic label."""
    return await _safe("add_topic", runtime.add_topic(name))


@mcp.tool()
async def remove_topic(topic_id: str) -> Any:
    """Stop tracking a topic, identified by its registry `topic_id`."""
    return await _safe("remove_topic", runtime.remove_topic(topic_id))


@mcp.tool()
async def get_digest() -> Any:
    """Return the current daily digest assembled by the OpenClaw Runtime."""
    return await _safe("get_digest", runtime.get_digest())


@mcp.tool()
async def trigger_analysis() -> Any:
    """Trigger an on-demand analysis run over the configured sources."""
    return await _safe("trigger_analysis", runtime.trigger_analysis())


# ── resources ────────────────────────────────────────────────────────────────


@mcp.resource("openclaw://digest")
async def digest_resource() -> str:
    """The current OpenClaw daily digest."""
    result = await _safe("digest_resource", runtime.get_digest())
    return result if isinstance(result, str) else str(result)


@mcp.resource("openclaw://topics")
async def topic_registry_resource() -> str:
    """Current state of the OpenClaw Topic Registry."""
    result = await _safe("topic_registry_resource", runtime.topic_registry_state())
    return str(result)


def main() -> None:
    """Run the MCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()
