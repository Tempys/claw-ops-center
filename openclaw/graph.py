from langchain_anthropic import ChatAnthropic
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from openclaw.config import OpenClawConfig


def build_graph(config: OpenClawConfig):
    llm = ChatAnthropic(
        model=config.llm.model,
        api_key=config.llm.api_key.get_secret_value(),
    )

    parts = ["You are a personal AI assistant. Be concise and direct."]
    if config.topics:
        parts.append(f"You are particularly focused on: {', '.join(config.topics)}.")
    system_prompt = "\n".join(parts)

    return create_react_agent(
        model=llm,
        tools=[],
        checkpointer=MemorySaver(),
        state_modifier=system_prompt,
    )
