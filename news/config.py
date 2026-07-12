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
    # Gmail integration (Epic 3). All optional — the email pipeline degrades to
    # a no-op when GMAIL_TOKEN_PATH does not exist yet.
    GMAIL_CREDENTIALS_PATH: str = "gmail_credentials.json"
    GMAIL_TOKEN_PATH: str = "gmail_token.json"
    GMAIL_SENDERS: str = ""  # comma-separated whitelist, e.g. "a@b.com,news@x.io"
    GMAIL_LABELS: str = ""  # comma-separated Gmail labels, e.g. "INBOX,Newsletters"
    GMAIL_SUBJECT_FILTER: str = ""  # optional subject contains-filter
    GMAIL_QUERY: str = ""  # raw extra Gmail search query, appended verbatim
    GMAIL_LOOKBACK: str = "1d"  # recency window (Gmail newer_than: 1d, 12h, 7d…)
    GMAIL_MAX_RESULTS: int = 25
    GMAIL_MARK_PROCESSED: bool = False  # label+mark-read fetched mail (mutates inbox)
    GMAIL_PROCESSED_LABEL: str = "OpenClawProcessed"
    OPENAI_API_KEY: str
    CHECKPOINT_DB_PATH: str = "checkpoints.db"

    model_config = {"case_sensitive": True}


try:
    _s = Settings()
except ValidationError as exc:
    raise ValueError(str(exc)) from exc


def __getattr__(name: str):
    return getattr(_s, name)
