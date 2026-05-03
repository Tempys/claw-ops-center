import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise ValueError(f"Required environment variable {key!r} is not set")
    return val


TELEGRAM_API_ID: int = int(_require("TELEGRAM_API_ID"))
TELEGRAM_API_HASH: str = _require("TELEGRAM_API_HASH")
TELEGRAM_CHANNEL_ID: str = _require("TELEGRAM_CHANNEL_ID")
TELEGRAM_BOT_TOKEN: str = _require("TELEGRAM_BOT_TOKEN")
TELEGRAM_DESTINATION_CHAT_ID: str = _require("TELEGRAM_DESTINATION_CHAT_ID")
EMAIL_HOST: str = _require("EMAIL_HOST")
EMAIL_PORT: int = int(os.environ.get("EMAIL_PORT", "993"))
EMAIL_USERNAME: str = _require("EMAIL_USERNAME")
EMAIL_PASSWORD: str = _require("EMAIL_PASSWORD")
OPENAI_API_KEY: str = _require("OPENAI_API_KEY")
CHECKPOINT_DB_PATH: str = os.environ.get("CHECKPOINT_DB_PATH", "checkpoints.db")
