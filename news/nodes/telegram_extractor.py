import asyncio
import logging
import re

import httpx

from news.state import EnrichedSignal, Signal, TelegramPipelineState

log = logging.getLogger(__name__)

_GITHUB_RE = re.compile(
    r"https?://github\.com/([^/\s\)\"\'\#,;!?]+)/([^/\s\)\"\'\#,;!?]+)",
    re.IGNORECASE,
)


async def _fetch_readme(owner: str, repo: str) -> str:
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"
    try:
        async with httpx.AsyncClient(timeout=5.0) as http:
            r = await http.get(url, follow_redirects=True)
            if r.status_code == 200:
                return r.text[:1500]
    except Exception:
        log.debug("README fetch failed for %s/%s", owner, repo)
    return ""


async def _enrich_one(signal: Signal) -> EnrichedSignal | None:
    m = _GITHUB_RE.search(signal["url"])
    if not m:
        return None
    owner, repo = m.group(1), m.group(2).rstrip("./")
    readme = await _fetch_readme(owner, repo)
    if not readme:
        return None
    return EnrichedSignal(
        github_link=f"https://github.com/{owner}/{repo}",
        readme=readme,
    )


async def telegram_extract_node(state: TelegramPipelineState) -> dict:
    # Collector returns {} on failure (e.g. Telegram auth error), leaving this
    # key unset; default to [] so one failing source degrades gracefully
    # instead of aborting the whole run.
    signals = state.get("telegram_raw_signals", [])
    results = await asyncio.gather(*(_enrich_one(s) for s in signals))
    enriched = [r for r in results if r is not None]
    return {
        "telegram_enriched_signals": enriched,
    }
