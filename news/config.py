from pathlib import Path

from pydantic_settings import BaseSettings

_ENV_FILE = Path(__file__).parent.parent / ".env"


class Settings(BaseSettings):
    TELEGRAM_API_ID: int
    TELEGRAM_API_HASH: str
    TELEGRAM_SESSION_STRING: str = ""
    TELEGRAM_CHANNEL_ID: str
    TELEGRAM_BOT_TOKEN: str
    TELEGRAM_DESTINATION_CHAT_ID: str
    EMAIL_HOST: str
    EMAIL_PORT: int = 993
    EMAIL_USERNAME: str
    EMAIL_PASSWORD: str
    OPENAI_API_KEY: str
    CHECKPOINT_DB_PATH: str = "checkpoints.db"

    model_config = {"env_file": str(_ENV_FILE), "case_sensitive": True}


_s = Settings()


def __getattr__(name: str):
    return getattr(_s, name)
