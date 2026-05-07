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
    source: str
    github_link: str
    readme: str


class EnrichNodeOutput(TypedDict):
    telegram_enriched_signals: list[EnrichedSignal]


def _list_union(a: list[str], b: list[str]) -> list[str]:
    """Merge two hash lists, preserving order and deduplicating."""
    seen = set(a)
    return a + [x for x in b if x not in seen]


class TelegramState(TypedDict):
    telegram_offset_id: int
    telegram_raw_signals: list[Signal]
    telegram_seen_hashes: Annotated[list[str], _list_union]
    telegram_enriched_signals: list[EnrichedSignal]
    filtered_signals: Annotated[list[Signal], operator.add]


class EmailState(TypedDict):
    email_last_checked: float
    email_raw_signals: list[Signal]
    email_seen_hashes: Annotated[list[str], _list_union]
    filtered_signals: Annotated[list[Signal], operator.add]


class State(TelegramState, EmailState):
    pass
