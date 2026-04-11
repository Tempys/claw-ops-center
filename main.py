import logging

from openclaw.config import load_config
from openclaw.orchestrator import Orchestrator
from openclaw.telegram_adapter import TelegramAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    config = load_config()
    print(f"OpenClaw starting — Telegram chat: {config.telegram.chat_id}")
    orchestrator = Orchestrator(config)
    adapter = TelegramAdapter(config, orchestrator)
    adapter.run()
