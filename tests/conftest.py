import os

# Set before any module imports so config.py does not raise at import time.
os.environ.setdefault("TELEGRAM_API_ID", "12345678")
os.environ.setdefault("TELEGRAM_API_HASH", "test_hash")
os.environ.setdefault("TELEGRAM_CHANNEL_ID", "-1001234567890")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "123:test_token")
os.environ.setdefault("TELEGRAM_DESTINATION_CHAT_ID", "-1009876543210")
os.environ.setdefault("EMAIL_HOST", "imap.test.com")
os.environ.setdefault("EMAIL_PORT", "993")
os.environ.setdefault("EMAIL_USERNAME", "test@test.com")
os.environ.setdefault("EMAIL_PASSWORD", "password")
os.environ.setdefault("OPENAI_API_KEY", "sk-openai-test")
os.environ.setdefault("CHECKPOINT_DB_PATH", ":memory:")
