import asyncio
import logging
import re

import httpx

from news.state import EnrichedSignal, EnrichNodeOutput, GitHubSignal, Signal, State

log = logging.getLogger(__name__)

_GITHUB_RE = re.compile(
    r"https?://github\.com/([^/\s\)\"\'\#,;!?]+)/([^/\s\)\"\'\#,;!?]+)",
    re.IGNORECASE,
)


def _extract_github(signal: Signal) -> GitHubSignal | None:
    text = signal["summary"] or signal["title"]
    m = _GITHUB_RE.search(text)
    if not m:
        return None
    return GitHubSignal(
        title=signal["title"],
        summary=signal["summary"],
        source=signal["source"],
        repo_owner=m.group(1),
        repo_name=m.group(2).rstrip("./"),
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
    gh = _extract_github(signal)
    if gh is None:
        return None
    readme = await _fetch_readme(gh["repo_owner"], gh["repo_name"])
    if not readme:
        return None
    github_link = f"https://github.com/{gh['repo_owner']}/{gh['repo_name']}"
    return EnrichedSignal(
        title=gh["title"],
        source=gh["source"],
        github_link=github_link,
        readme=readme,
    )


async def telegram_enrich_node(state: State) -> EnrichNodeOutput:
    signals = state["telegram_raw_signals"]
    results = await asyncio.gather(*(_enrich_one(s) for s in signals))
    return EnrichNodeOutput(telegram_enriched_signals=[r for r in results if r is not None])
