# news/runner.py
import asyncio

asyncio.set_event_loop(
    asyncio.new_event_loop()
)  # pyrogram sync.py calls get_event_loop() at import time (Python 3.12+ no longer auto-creates one)

import logging  # noqa: E402
import time  # noqa: E402

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver  # noqa: E402

import news.config as config  # noqa: E402
from news.graph import create_graph  # noqa: E402
from news.state import State  # noqa: E402

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_RUN_CONFIG = {"configurable": {"thread_id": "main"}}

# Fields that reset on every run (transient pipeline outputs).
# telegram_offset_id is intentionally absent — the checkpointer owns it after the first run.
_RUN_INPUT = {
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": time.time(),
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": None,  # None triggers _replace_or_add to reset to [] each run
}

# Seed used only when no checkpoint exists yet (first ever run).
_FIRST_RUN_SEED: State = {**_RUN_INPUT, "telegram_offset_id": 0}  # type: ignore[typeddict-item]


async def main() -> None:
    async with AsyncSqliteSaver.from_conn_string(
        config.CHECKPOINT_DB_PATH
    ) as checkpointer:
        graph = create_graph().compile(checkpointer=checkpointer)
        snapshot = await graph.aget_state(_RUN_CONFIG)
        invoke_input = _FIRST_RUN_SEED if not snapshot.values else _RUN_INPUT
        try:
            await graph.ainvoke(invoke_input, config=_RUN_CONFIG)
            log.info("Run completed successfully")
        except Exception as exc:
            log.error(f"Run failed: {exc}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
