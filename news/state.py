import operator
from typing import Annotated, Literal
from typing_extensions import TypedDict


CLASSIFICATION = Literal[
    "ai_agent_framework",
    "llm_finetuning",
    "skill_plugin_builder",
    "code_generation",
    "dev_productivity",
    "prompt_engineering",
    "other",
    "error",
]


class Signal(TypedDict):
    title: str
    classification: CLASSIFICATION
    summary: str
    source: str


class GitHubSignal(TypedDict):
    title: str
    summary: str
    source: str
    repo_owner: str
    repo_name: str


class EnrichedSignal(TypedDict):
    title: str
    summary: str
    source: str
    repo_owner: str
    repo_name: str
    readme_excerpt: str


def _list_union(a: list[str], b: list[str]) -> list[str]:
    """Merge two hash lists, preserving order and deduplicating."""
    seen = set(a)
    return a + [x for x in b if x not in seen]


class State(TypedDict):
    # Telegram pipeline
    telegram_offset_id: int
    telegram_raw_signals: list[Signal]
    telegram_seen_hashes: Annotated[list[str], _list_union]
    telegram_enriched_signals: list[EnrichedSignal]
    # Email pipeline
    email_last_checked: float
    email_raw_signals: list[Signal]
    email_seen_hashes: Annotated[list[str], _list_union]
    # Fan-in — both pipelines append here via operator.add
    filtered_signals: Annotated[list[Signal], operator.add]
