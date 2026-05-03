import asyncio
asyncio.set_event_loop(asyncio.new_event_loop())  # pyrogram sync.py calls get_event_loop() at import time (Python 3.12+ no longer auto-creates one)

import logging
import time

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

import news.config as config
from news.graph import create_graph
from news.state import State

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_RUN_CONFIG = {"configurable": {"thread_id": "main"}}

# email_last_checked initialised to now so the first run does not sweep all history
_INITIAL_STATE: State = {
    "telegram_offset_id": 0,
    "email_last_checked": time.time(),
    "signals": [],
    "filtered_signals": [],
}


async def main() -> None:
    async with AsyncSqliteSaver.from_conn_string(config.CHECKPOINT_DB_PATH) as checkpointer:
        graph = create_graph().compile(checkpointer=checkpointer)
        try:
            await graph.ainvoke(_INITIAL_STATE, config=_RUN_CONFIG)
            log.info("Run completed successfully")
        except Exception as exc:
            log.error(f"Run failed: {exc}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
