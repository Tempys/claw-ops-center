import logging

from langgraph.checkpoint.sqlite import SqliteSaver

from openclaw.config import load_config
from openclaw.graph import build_graph
from openclaw.telegram_adapter import TelegramAdapter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

log = logging.getLogger(__name__)

if __name__ == "__main__":
    config = load_config()
    log.info("OpenClaw starting — Telegram chat: %s", config.telegram.chat_id)
    with SqliteSaver.from_conn_string(config.sqlite_path) as checkpointer:
        graph = build_graph(config, checkpointer)
        adapter = TelegramAdapter(config, graph)
        adapter.run()
