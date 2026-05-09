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
    telegram_id: int
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


class ExtractNodeOutput(TypedDict):
    telegram_id: int
    github_link: str
    readme: str


class EnrichedSignal(TypedDict):
    title: str
    source: str
    github_link: str
    readme: str


def _list_union(a: list[str], b: list[str]) -> list[str]:
    """Merge two hash lists, preserving order and deduplicating."""
    seen = set(a)
    return a + [x for x in b if x not in seen]


class State(TypedDict):
    """Persistent state — survives across scheduler invocations."""
    telegram_offset_id: int
    email_last_checked: float
    email_seen_hashes: Annotated[list[str], _list_union]

class TelegramPipelineState(State):
    """Transient telegram fields, only needed within the telegram sub-graph."""
    telegram_raw_signals: list[Signal]
    telegram_enriched_signals: list[EnrichedSignal]
    telegram_id: list[int]


class EmailState(TypedDict):
    email_last_checked: float
    email_raw_signals: list[Signal]
    email_seen_hashes: Annotated[list[str], _list_union]
    filtered_signals: Annotated[list[Signal], operator.add]
