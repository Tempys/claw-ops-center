# news/pipelines/email.py
from langgraph.graph import END, START, StateGraph

from news.nodes.email_collector import email_collector_node
from news.nodes.email_dedup import email_dedup_node
from news.nodes.email_analyzer import email_analyze_node
from news.state import State


def build_email_pipeline():
    builder = StateGraph(State)
    builder.add_node("collect", email_collector_node)
    builder.add_node("dedup", email_dedup_node)
    builder.add_node("analyze", email_analyze_node)
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "dedup")
    builder.add_edge("dedup", "analyze")
    builder.add_edge("analyze", END)
    return builder.compile()
