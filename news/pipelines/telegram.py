# news/pipelines/telegram.py
from langgraph.graph import END, START, StateGraph

from news.nodes.telegram_collector import telegram_collector_node
from news.nodes.telegram_dedup import telegram_dedup_node
from news.nodes.telegram_analyzer import telegram_analyze_node
from news.state import State


def build_telegram_pipeline():
    builder = StateGraph(State)
    builder.add_node("collect", telegram_collector_node)
    builder.add_node("dedup", telegram_dedup_node)
    builder.add_node("analyze", telegram_analyze_node)
    builder.add_edge(START, "collect")
    builder.add_edge("collect", "dedup")
    builder.add_edge("dedup", "analyze")
    builder.add_edge("analyze", END)
    return builder.compile()
