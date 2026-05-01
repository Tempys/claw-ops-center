import pytest

from openclaw.config import _substitute_env_vars, load_config


def test_substitute_env_vars_happy_path(monkeypatch):
    monkeypatch.setenv("MY_VAR", "the_value")
    result = _substitute_env_vars("value is ${MY_VAR}")
    assert result == "value is the_value"


def test_substitute_env_vars_missing_key(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)
    with pytest.raises(ValueError, match="MISSING_VAR"):
        _substitute_env_vars("${MISSING_VAR}")


def test_load_config_happy_path(tmp_path, monkeypatch):
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "telegram:\n"
        "  bot_token: \"${TEST_BOT_TOKEN}\"\n"
        "  chat_id: \"12345\"\n"
        "llm:\n"
        "  api_key: \"${TEST_API_KEY}\"\n"
        "topics:\n"
        "  - Python\n"
    )

    monkeypatch.setenv("TEST_BOT_TOKEN", "bot123:secret")
    monkeypatch.setenv("TEST_API_KEY", "sk-test-key")

    config = load_config(config_file)

    assert config.telegram.bot_token.get_secret_value() == "bot123:secret"
    assert config.telegram.chat_id == "12345"
    assert config.llm.api_key.get_secret_value() == "sk-test-key"
    assert config.topics == ["Python"]
    assert config.sqlite_path == "openclaw.db"
