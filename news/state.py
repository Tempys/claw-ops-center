from typing import Annotated
import operator
from typing_extensions import TypedDict


class Signal(TypedDict):
    title: str
    classification: str  # "urgent" | "informational" | "noise" | "error"
    summary: str
    source: str          # "telegram" | "email"


class State(TypedDict):
    telegram_offset_id: int
    email_last_checked: float
    signals: Annotated[list[Signal], operator.add]
    analysis: str
