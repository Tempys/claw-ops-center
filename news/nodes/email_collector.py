import asyncio
import email
import imaplib
import logging
import time
from datetime import datetime
from email.header import decode_header as _raw_decode

import news.config as config
from news.state import Signal, State

log = logging.getLogger(__name__)


def _decode(value) -> str:
    if value is None:
        return ""
    parts = _raw_decode(str(value))
    out = []
    for part, enc in parts:
        if isinstance(part, bytes):
            out.append(part.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(part)
    return " ".join(out)


def _body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                return payload.decode("utf-8", errors="replace")[:1000] if payload else ""
    payload = msg.get_payload(decode=True)
    return payload.decode("utf-8", errors="replace")[:1000] if payload else ""


def fetch_emails_since(since_timestamp: float) -> list[dict]:
    since_date = datetime.fromtimestamp(since_timestamp).strftime("%d-%b-%Y")
    results = []
    with imaplib.IMAP4_SSL(config.EMAIL_HOST, config.EMAIL_PORT) as imap:
        imap.login(config.EMAIL_USERNAME, config.EMAIL_PASSWORD)
        imap.select("INBOX")
        _, msg_ids = imap.search(None, f"SINCE {since_date}")
        for msg_id in (msg_ids[0].split() if msg_ids[0] else []):
            _, data = imap.fetch(msg_id, "(RFC822)")
            msg = email.message_from_bytes(data[0][1])
            results.append({
                "subject": _decode(msg.get("Subject")),
                "body": _body(msg),
                "sender": _decode(msg.get("From")),
            })
    return results


async def email_collector_node(state: State) -> dict:
    try:
        now = time.time()
        emails = await asyncio.to_thread(fetch_emails_since, state["email_last_checked"])
        signals = [
            Signal(
                title=e["subject"] or "(no subject)",
                classification="other",
                summary=e["body"],
                source="email",
            )
            for e in emails
        ]
        return {"email_last_checked": now, "email_raw_signals": signals}
    except Exception as exc:
        log.error(f"Email collector failed: {exc}", exc_info=True)
        return {
            "email_raw_signals": [Signal(
                title="Email collector failed",
                classification="error",
                summary=str(exc),
                source="email",
            )]
        }
