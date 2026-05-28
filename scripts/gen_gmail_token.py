"""Run once to authorize Gmail access and store an OAuth2 token.

Prerequisite: a Google Cloud OAuth *client secrets* JSON (Desktop app type)
downloaded to the path in GMAIL_CREDENTIALS_PATH (default: gmail_credentials.json).
Enable the Gmail API in the same Google Cloud project first.

This opens a browser for consent, then writes a token (with refresh token) to
GMAIL_TOKEN_PATH. The pipeline reads that token and refreshes it automatically.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import news.config as config  # noqa: E402
from news.nodes.gmail_client import _SCOPES  # noqa: E402


def main() -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds_path = Path(config.GMAIL_CREDENTIALS_PATH)
    if not creds_path.exists():
        raise SystemExit(
            f"OAuth client secrets not found at {creds_path}.\n"
            "Download it from Google Cloud Console "
            "(APIs & Services -> Credentials -> OAuth client ID -> Desktop app) "
            "and set GMAIL_CREDENTIALS_PATH if you saved it elsewhere."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(creds_path), _SCOPES)
    # offline + consent prompt guarantees a refresh_token is returned.
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")

    token_path = Path(config.GMAIL_TOKEN_PATH)
    token_path.write_text(creds.to_json(), encoding="utf-8")
    print(f"\nSaved Gmail token to {token_path.resolve()}")


if __name__ == "__main__":
    main()
