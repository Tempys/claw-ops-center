# Research: OpenClaw Assistant Orchestrator

## OpenClaw's Recommended Architecture

### Core Pattern: Gateway + ReAct Loop

OpenClaw runs a **single long-lived orchestration process** (the Gateway) that owns:
- Session management (one stateful session per conversation)
- Routing inbound messages from channels (Telegram, Slack, etc.)
- A **Command Queue** — serialized message processing (one message at a time per session)
- Context assembly before every LLM call
- Streaming responses back through the originating channel

### Message Flow (Telegram → LLM → Telegram)
```
Telegram message
  → Channel Adapter (normalize)
  → Session Lookup / Create
  → Context Assembly:
      - core agent instructions (system prompt)
      - skills list (compact)
      - message history
      - per-run overrides
  → LLM Inference (ReAct loop)
  → Tool Execution (if tool calls returned)
  → Stream response back to Telegram
  → Persist to session history
```

### ReAct Loop
`intake → context assembly → model inference → tool execution → streaming replies → persistence`

Repeats until the model returns final text (no more tool calls).

### Session Model
- Stateful: holds message history
- **Serialized**: one message processed at a time (Command Queue)
- Prevents concurrent tool conflicts

### Tool / Skills Layer
- Skills are Markdown files loaded on-demand
- External tools via MCP (standardized interfaces)
- Agent never directly touches services — always via tool abstraction

---

## Recommended Python Stack

| Concern | Library |
|---------|---------|
| Telegram bot | `python-telegram-bot` (v21+, async) |
| LLM calls | `anthropic` Python SDK |
| Config | Already set up: Pydantic + YAML (see `openclaw/config.py`) |
| Async runtime | `asyncio` (built-in) |
| Message queue | `asyncio.Queue` (simple, in-process serialization) |

---

## Key Design Decisions (aligned with OpenClaw)

1. **Single orchestrator class** owns the session and the ReAct loop
2. **asyncio.Queue** for command serialization (one message at a time)
3. **Context assembler** builds messages list before every inference call
4. **Tool dispatch** handled inside the loop before returning to model
5. **Telegram adapter** normalizes updates into internal `Message` objects

---

## Constraints / Gotchas

- `python-telegram-bot` v21+ is fully async — must use `Application` builder pattern
- Anthropic SDK streaming: use `client.messages.stream()` for real-time Telegram typing indicators
- Keep session history bounded (e.g. last N turns) to stay within context limits
- Bot token is already in config as `telegram.bot_token` (SecretStr)
