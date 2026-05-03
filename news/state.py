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


class State(TypedDict):
    telegram_offset_id: int
    email_last_checked: float
    signals: Annotated[list[Signal], operator.add]
    analysis: str
