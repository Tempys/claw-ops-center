from typing import Annotated
from typing_extensions import TypedDict
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AnyMessage, SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.graph.state import CompiledStateGraph

from openclaw.config import OpenClawConfig


class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph(config: OpenClawConfig, checkpointer: BaseCheckpointSaver) -> CompiledStateGraph:
    llm = ChatAnthropic(
        model=config.llm.model,
        api_key=config.llm.api_key.get_secret_value(),
    )

    parts = ["You are a personal AI assistant. Be concise and direct."]
    if config.topics:
        parts.append(f"You are particularly focused on: {', '.join(config.topics)}.")
    system_prompt = SystemMessage(content="\n".join(parts))

    async def call_model(state: State) -> dict:
        response = await llm.ainvoke([system_prompt] + state["messages"])
        return {"messages": [response]}

    graph = StateGraph(State)
    graph.add_node("llm", call_model)
    graph.add_edge(START, "llm")
    graph.add_edge("llm", END)

    return graph.compile(checkpointer=checkpointer)
