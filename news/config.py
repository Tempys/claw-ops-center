from pathlib import Path

import dotenv
from pydantic import ValidationError
from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).parent.parent / ".env"

dotenv.load_dotenv(_ENV_FILE)


class Settings(BaseSettings):
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_SESSION_STRING: str = ""
    TELEGRAM_CHANNEL_ID: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_DESTINATION_CHAT_ID: str
    EMAIL_HOST: str = ""
    EMAIL_PORT: int = 993
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    OPENAI_API_KEY: str
    CHECKPOINT_DB_PATH: str = "checkpoints.db"

    model_config = {"case_sensitive": True}


try:
    _s = Settings()
except ValidationError as exc:
    raise ValueError(str(exc)) from exc


def __getattr__(name: str):
    return getattr(_s, name)
