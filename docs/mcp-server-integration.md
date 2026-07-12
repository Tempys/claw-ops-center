# OpenClaw Custom MCP Server — Integration Guide

Epic 2. Exposes the OpenClaw Runtime to MCP-compatible AI assistants over **stdio**.

> **Status:** the server is fully wired but backed by `StubRuntime` — every tool
> returns `{"status": "not_implemented", ...}` until the OpenClaw Runtime
> internals (Epic 1: Topic Registry, Digest Composer, Analysis Engine) exist.
> Swapping in a real implementation is a one-line change to `runtime` in
> `news/mcp_server/server.py`; no client reconfiguration is needed.

## What it exposes

| Type | Name | Purpose |
|------|------|---------|
| tool | `list_topics` | List tracked topics |
| tool | `add_topic(name)` | Track a new topic |
| tool | `remove_topic(topic_id)` | Stop tracking a topic |
| tool | `get_digest` | Current daily digest |
| tool | `trigger_analysis` | On-demand analysis run |
| resource | `openclaw://digest` | Current digest |
| resource | `openclaw://topics` | Topic registry state |

## Run it directly

```bash
uv run python -m news.mcp_server
```

It speaks the MCP protocol on stdio, so there's nothing to see when run by hand —
it's meant to be launched by a client.

## Claude Code

```bash
claude mcp add openclaw -- uv run python -m news.mcp_server
```

Run from the repo root (the `uv run` resolves this project's environment). Then
`/mcp` to confirm it connects, after which the five tools are available.

Alternatively, commit a project-scoped `.mcp.json` at the repo root:

```json
{
  "mcpServers": {
    "openclaw": {
      "command": "uv",
      "args": ["run", "python", "-m", "news.mcp_server"]
    }
  }
}
```

## OpenAI Codex

Codex reads MCP servers from its config (`~/.codex/config.toml`):

```toml
[mcp_servers.openclaw]
command = "uv"
args = ["run", "python", "-m", "news.mcp_server"]
```

Any MCP client that supports stdio servers can connect the same way: run
`uv run python -m news.mcp_server` as the command from the repo root.

## Single-user auth

stdio transport means the client launches the server as a local subprocess under
the user's own account — there is no network listener and no shared endpoint, so
access is scoped to the single local user by construction.
