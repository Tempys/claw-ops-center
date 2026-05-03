from langgraph.graph import END, START, StateGraph

from openclaw.nodes.analyzer import analyze_and_classify_node
from openclaw.nodes.email_collector import email_collector_node
from openclaw.nodes.sender import sender_node
from openclaw.nodes.telegram_collector import telegram_collector_node
from openclaw.state import State


def build_graph_builder() -> StateGraph:
    builder = StateGraph(State)

    builder.add_node("telegram_collector", telegram_collector_node)
    builder.add_node("email_collector", email_collector_node)
    builder.add_node("analyze_and_classify", analyze_and_classify_node)
    builder.add_node("sender", sender_node)

    builder.add_edge(START, "telegram_collector")
    builder.add_edge(START, "email_collector")
    builder.add_edge("telegram_collector", "analyze_and_classify")
    builder.add_edge("email_collector", "analyze_and_classify")
    builder.add_edge("analyze_and_classify", "sender")
    builder.add_edge("sender", END)

    return builder
