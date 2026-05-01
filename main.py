import logging

from openclaw.config import load_config
from openclaw.graph import build_graph
from openclaw.telegram_adapter import TelegramAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    config = load_config()
    print(f"OpenClaw starting — Telegram chat: {config.telegram.chat_id}")
    graph = build_graph(config)
    adapter = TelegramAdapter(config, graph)
    adapter.run()
