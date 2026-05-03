"""
Run once to generate a Pyrogram session string.
Paste the printed value into .env as TELEGRAM_SESSION_STRING.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv()

from pyrogram import Client

API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]


async def main() -> None:
    async with Client("gen_session_tmp", api_id=API_ID, api_hash=API_HASH) as client:
        string = await client.export_session_string()
    print("\nAdd this to your .env:\n")
    print(f"TELEGRAM_SESSION_STRING={string}\n")


if __name__ == "__main__":
    asyncio.run(main())
