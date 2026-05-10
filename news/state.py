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
    url: str


class ExtractNodeOutput(TypedDict):
    telegram_id: int
    github_link: str
    readme: str


class EnrichedSignal(TypedDict):
    github_link: str
    readme: str


class AnalyzedSignal(TypedDict):
    github_link: str
    summary: str


def _take_max(a: float, b: float) -> float:
    return max(a, b)


def _list_union(a: list[str], b: list[str]) -> list[str]:
    """Merge two hash lists, preserving order and deduplicating."""
    seen = set(a)
    return a + [x for x in b if x not in seen]


def _replace_or_add(a: list | None, b: list | None) -> list:
    """Reset to [] when b is None; otherwise accumulate (for parallel branches)."""
    if b is None:
        return []
    if a is None:
        return list(b)
    return a + b


class State(TypedDict):
    """Persistent state — survives across scheduler invocations."""

    telegram_offset_id: int
    email_last_checked: Annotated[float, _take_max]
    email_seen_hashes: Annotated[list[str], _list_union]
    filtered_signals: Annotated[list[AnalyzedSignal], _replace_or_add]


class TelegramPipelineState(State):
    """Transient telegram fields, only needed within the telegram sub-graph."""

    telegram_raw_signals: list[Signal]
    telegram_enriched_signals: list[EnrichedSignal]
    telegram_id: list[int]


class EmailState(TypedDict):
    email_last_checked: Annotated[float, _take_max]
    email_raw_signals: list[Signal]
    email_seen_hashes: Annotated[list[str], _list_union]
