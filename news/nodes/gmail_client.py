"""Gmail API client for the email pipeline (Epic 3: Gmail Integration).

Uses the Gmail REST API with OAuth2 (single-user, offline token refresh) — see
``scripts/gen_gmail_token.py`` for the one-time consent flow that produces the
token file at ``config.GMAIL_TOKEN_PATH``.

Heavy Google libraries are imported lazily inside functions (matching the
repo's lazy-import convention for Pyrogram/telegram), so importing this module
is cheap and works even before ``google-*`` packages are installed. The token
file is checked before any Google import, so an unconfigured environment fails
fast with ``FileNotFoundError`` rather than an import error.
"""

import base64
import logging
import re
from html import unescape
from pathlib import Path

import news.config as config

log = logging.getLogger(__name__)

# gmail.modify covers reading messages and applying the "processed" label /
# marking read. Use readonly instead if GMAIL_MARK_PROCESSED stays off and you
# want to guarantee the integration never mutates the mailbox.
_SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


# ── credentials / service ────────────────────────────────────────────────────


def _load_credentials():
    """Load OAuth2 credentials, refreshing (and re-persisting) if expired.

    Raises FileNotFoundError before importing any Google library when the token
    file is missing, so unconfigured environments degrade gracefully.
    """
    token_path = Path(config.GMAIL_TOKEN_PATH)
    if not token_path.exists():
        raise FileNotFoundError(
            f"Gmail token not found at {token_path}. "
            "Run: uv run python scripts/gen_gmail_token.py"
        )

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials

    creds = Credentials.from_authorized_user_file(str(token_path), _SCOPES)
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_path.write_text(creds.to_json(), encoding="utf-8")
        return creds
    raise RuntimeError(
        "Gmail credentials are invalid and cannot be refreshed; "
        "re-run scripts/gen_gmail_token.py"
    )


def _build_service():
    creds = _load_credentials()
    from googleapiclient.discovery import build

    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# ── query building ───────────────────────────────────────────────────────────


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


def _build_query() -> str:
    """Build a Gmail search query from the configured filters.

    Recency is bounded by ``newer_than`` (GMAIL_LOOKBACK), not the run's
    ``email_last_checked`` timestamp: the runner overwrites that with the
    current time on every run (``_take_max`` reducer), so it is unusable as a
    'since' bound. Dedup of already forwarded mail is handled downstream by
    ``email_dedup_node``; turning on GMAIL_MARK_PROCESSED adds Gmail-side dedup
    via the ``-label:<processed>`` clause below.
    """
    parts: list[str] = []

    senders = _split(config.GMAIL_SENDERS)
    if senders:
        parts.append("(" + " OR ".join(f"from:{s}" for s in senders) + ")")

    labels = _split(config.GMAIL_LABELS)
    if labels:
        parts.append("(" + " OR ".join(f"label:{lab}" for lab in labels) + ")")

    if config.GMAIL_SUBJECT_FILTER:
        parts.append(f"subject:({config.GMAIL_SUBJECT_FILTER})")

    if config.GMAIL_LOOKBACK:
        parts.append(f"newer_than:{config.GMAIL_LOOKBACK}")

    if config.GMAIL_MARK_PROCESSED and config.GMAIL_PROCESSED_LABEL:
        parts.append(f"-label:{config.GMAIL_PROCESSED_LABEL}")

    if config.GMAIL_QUERY:
        parts.append(config.GMAIL_QUERY)

    return " ".join(parts)


# ── message parsing ──────────────────────────────────────────────────────────


def _decode(data: str) -> str:
    """Decode a base64url-encoded Gmail body part, tolerating missing padding."""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii")).decode(
        "utf-8", errors="replace"
    )


def _walk(payload: dict) -> tuple[str, str]:
    """Recursively collect (plain_text, html) bodies from a MIME payload tree."""
    plain, html = "", ""
    data = payload.get("body", {}).get("data")
    mime = payload.get("mimeType", "")
    if data:
        if mime == "text/plain":
            plain += _decode(data)
        elif mime == "text/html":
            html += _decode(data)
    for part in payload.get("parts", []) or []:
        p, h = _walk(part)
        plain += p
        html += h
    return plain, html


_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE
)
_TAG_RE = re.compile(r"<[^>]+>")
_INLINE_WS_RE = re.compile(r"[ \t\r\f\v]+")
_EXTRA_NL_RE = re.compile(r"\n{3,}")


def _html_to_text(html: str) -> str:
    text = _SCRIPT_STYLE_RE.sub(" ", html)
    text = _TAG_RE.sub(" ", text)
    text = unescape(text)
    text = _INLINE_WS_RE.sub(" ", text)
    text = _EXTRA_NL_RE.sub("\n\n", text)
    return text.strip()


def _extract_body(payload: dict) -> str:
    """Return the email body as text, preferring text/plain over stripped HTML."""
    plain, html = _walk(payload)
    if plain.strip():
        return plain.strip()
    if html.strip():
        return _html_to_text(html)
    return ""


def _parse_message(msg: dict) -> dict:
    payload = msg.get("payload", {})
    headers = {h["name"].lower(): h["value"] for h in payload.get("headers", []) or []}
    return {
        "id": msg["id"],
        "thread_id": msg.get("threadId", ""),
        "subject": headers.get("subject", ""),
        "sender": headers.get("from", ""),
        "snippet": msg.get("snippet", ""),
        "body": _extract_body(payload),
        "label_ids": msg.get("labelIds", []),
        "permalink": f"https://mail.google.com/mail/u/0/#all/{msg['id']}",
    }


# ── public API (called from email_collector_node via asyncio.to_thread) ──────


def fetch_recent_emails() -> list[dict]:
    """Fetch recent emails matching the configured filters via the Gmail API.

    Synchronous (the Google client is blocking); the caller wraps this in
    ``asyncio.to_thread``. Returns parsed message dicts (see ``_parse_message``).
    """
    service = _build_service()
    query = _build_query()
    log.info("Gmail query: %s", query or "(none)")

    listing = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=config.GMAIL_MAX_RESULTS)
        .execute()
    )

    out: list[dict] = []
    for ref in listing.get("messages", []) or []:
        full = (
            service.users()
            .messages()
            .get(userId="me", id=ref["id"], format="full")
            .execute()
        )
        out.append(_parse_message(full))
    return out


def _ensure_label(service, name: str) -> str:
    existing = service.users().labels().list(userId="me").execute().get("labels", [])
    for label in existing:
        if label["name"].lower() == name.lower():
            return label["id"]
    created = (
        service.users()
        .labels()
        .create(
            userId="me",
            body={
                "name": name,
                "labelListVisibility": "labelShow",
                "messageListVisibility": "show",
            },
        )
        .execute()
    )
    return created["id"]


def mark_processed(message_ids: list[str]) -> None:
    """Apply the configured 'processed' label and mark messages read.

    Only invoked when GMAIL_MARK_PROCESSED is enabled. Combined with the
    ``-label:<processed>`` clause in ``_build_query``, this prevents the same
    email from being re-ingested on later runs.
    """
    if not message_ids:
        return
    service = _build_service()
    label_id = _ensure_label(service, config.GMAIL_PROCESSED_LABEL)
    body = {"addLabelIds": [label_id], "removeLabelIds": ["UNREAD"]}
    for mid in message_ids:
        service.users().messages().modify(userId="me", id=mid, body=body).execute()
