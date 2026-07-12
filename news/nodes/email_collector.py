import asyncio
import logging

import news.config as config
from news.nodes import gmail_client
from news.state import EmailState

log = logging.getLogger(__name__)


def _to_signal(msg: dict) -> dict:
    """Map a fetched Gmail message to the email-pipeline signal shape.

    Matches the dict shape the rest of the email pipeline expects:
    ``url`` (used for dedup hashing + dropped into the classifier),
    ``title`` (subject), ``summary`` (body excerpt), ``source``.
    """
    return {
        "url": msg["permalink"],
        "title": msg.get("subject", ""),
        "summary": (msg.get("body") or msg.get("snippet") or "")[:1500],
        "source": "email",
    }


async def email_collector_node(state: EmailState) -> dict:
    """Fetch recent Gmail messages and emit them as raw email signals.

    Degrades gracefully: if Gmail is not configured (no OAuth token) or the API
    call fails, logs and returns an empty list so the rest of the run proceeds.
    Run ``scripts/gen_gmail_token.py`` once to create the token.
    """
    try:
        emails = await asyncio.to_thread(gmail_client.fetch_recent_emails)
    except Exception as exc:
        log.warning("Gmail collector skipped: %s", exc)
        return {"email_raw_signals": []}

    signals = [_to_signal(m) for m in emails]

    if config.GMAIL_MARK_PROCESSED and emails:
        try:
            await asyncio.to_thread(
                gmail_client.mark_processed, [m["id"] for m in emails]
            )
        except Exception as exc:
            log.warning("Gmail mark-processed failed: %s", exc)

    log.info("Gmail collector produced %d signal(s)", len(signals))
    return {"email_raw_signals": signals}
