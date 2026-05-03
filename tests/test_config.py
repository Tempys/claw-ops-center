import importlib
import os
from unittest.mock import patch


def test_config_reads_all_env_vars():
    import news.config as cfg
    importlib.reload(cfg)
    assert cfg.TELEGRAM_API_ID == 12345678
    assert cfg.TELEGRAM_API_HASH == "test_hash"
    assert cfg.TELEGRAM_CHANNEL_ID == "-1001234567890"
    assert cfg.TELEGRAM_BOT_TOKEN == "123:test_token"
    assert cfg.TELEGRAM_DESTINATION_CHAT_ID == "-1009876543210"
    assert cfg.EMAIL_HOST == "imap.test.com"
    assert cfg.EMAIL_PORT == 993
    assert cfg.EMAIL_USERNAME == "test@test.com"
    assert cfg.EMAIL_PASSWORD == "password"
    assert cfg.ANTHROPIC_API_KEY == "sk-ant-test"


def test_config_default_checkpoint_path():
    env = dict(os.environ)
    env.pop("CHECKPOINT_DB_PATH", None)
    with patch.dict(os.environ, env, clear=True):
        import news.config as cfg
        importlib.reload(cfg)
        assert cfg.CHECKPOINT_DB_PATH == "checkpoints.db"


def test_missing_required_var_raises():
    env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        import news.config as cfg
        import pytest
        with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
            importlib.reload(cfg)
