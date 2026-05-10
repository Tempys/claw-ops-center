"""
Run once to generate a Pyrogram session string.
Paste the printed value into .env as TELEGRAM_SESSION_STRING.
"""
import asyncio
import functools
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

# Pyrogram's ainput uses the deprecated asyncio.get_event_loop() which breaks
# on Python 3.10+ inside a running coroutine. Patch it to use get_running_loop().
async def _ainput(prompt: str = "", *, hide: bool = False) -> str:
    with ThreadPoolExecutor(1) as executor:
        func = functools.partial(getpass if hide else input, prompt)
        result = await asyncio.get_running_loop().run_in_executor(executor, func)
    return result.strip()

import pyrogram.utils
import pyrogram.client
pyrogram.utils.ainput = _ainput
pyrogram.client.ainput = _ainput

from pyrogram import Client

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
PHONE = os.environ.get("TELEGRAM_PHONE") or None


async def main() -> None:
    async with Client(
        "gen_session_tmp",
        api_id=API_ID,
        api_hash=API_HASH,
        phone_number=PHONE,
    ) as client:
        string = await client.export_session_string()

    session_file = "gen_session_tmp.session"
    if os.path.exists(session_file):
        os.remove(session_file)

    print("\nAdd this to your .env:\n")
    print(f"TELEGRAM_SESSION_STRING={string}\n")


if __name__ == "__main__":
    asyncio.run(main())
