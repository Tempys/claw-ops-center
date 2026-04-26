import os
import re
import yaml
from pathlib import Path
from pydantic import BaseModel, SecretStr
from dotenv import load_dotenv


class TelegramConfig(BaseModel):
    bot_token: SecretStr
    chat_id: str


class OpenClawConfig(BaseModel):
    telegram: TelegramConfig
    topics: list[str] = []


def _substitute_env_vars(text: str) -> str:
    return re.sub(
        r'\$\{([^}]+)\}',
        lambda m: os.environ[m.group(1)],
        text
    )


def load_config(path: str | Path = "config.yaml") -> OpenClawConfig:
    load_dotenv()
    raw = Path(path).read_text()
    substituted = _substitute_env_vars(raw)
    data = yaml.safe_load(substituted)
    return OpenClawConfig.model_validate(data)
