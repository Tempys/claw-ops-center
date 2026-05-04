# news/graph.py
from langgraph.graph import END, START, StateGraph

from news.pipelines.telegram import build_telegram_pipeline
from news.pipelines.email import build_email_pipeline
from news.nodes.sender import sender_node
from news.state import State


async def _merge_node(state: State) -> dict:
    return {}


def _route_after_merge(state: State) -> str:
    return "sender" if state.get("filtered_signals") else END


def create_graph() -> StateGraph:
    builder = StateGraph(State)

    builder.add_node("telegram_pipeline", build_telegram_pipeline())
    builder.add_node("email_pipeline", build_email_pipeline())
    builder.add_node("merge", _merge_node)
    builder.add_node("sender", sender_node)

    builder.add_edge(START, "telegram_pipeline")
    builder.add_edge(START, "email_pipeline")
    builder.add_edge("telegram_pipeline", "merge")
    builder.add_edge("email_pipeline", "merge")
    builder.add_conditional_edges("merge", _route_after_merge, {"sender": "sender", END: END})
    builder.add_edge("sender", END)

    return builder


def make_graph(config: dict | None = None):
    return create_graph().compile()
