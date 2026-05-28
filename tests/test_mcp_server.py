import pytest

from news.mcp_server import server
from news.mcp_server.runtime import NotImplementedRuntimeError, StubRuntime

_EXPECTED_TOOLS = {
    "list_topics",
    "add_topic",
    "remove_topic",
    "get_digest",
    "trigger_analysis",
}


async def test_stub_runtime_raises_not_implemented():
    rt = StubRuntime()
    with pytest.raises(NotImplementedRuntimeError):
        await rt.list_topics()
    with pytest.raises(NotImplementedRuntimeError):
        await rt.add_topic("x")
    with pytest.raises(NotImplementedRuntimeError):
        await rt.remove_topic("x")
    with pytest.raises(NotImplementedRuntimeError):
        await rt.get_digest()
    with pytest.raises(NotImplementedRuntimeError):
        await rt.trigger_analysis()
    with pytest.raises(NotImplementedRuntimeError):
        await rt.topic_registry_state()


async def test_server_registers_expected_tools():
    tools = await server.mcp.list_tools()
    assert {t.name for t in tools} == _EXPECTED_TOOLS


async def test_server_registers_expected_resources():
    resources = await server.mcp.list_resources()
    uris = {str(r.uri) for r in resources}
    assert "openclaw://digest" in uris
    assert "openclaw://topics" in uris


async def test_tools_return_not_implemented_with_stub_runtime():
    digest = await server.get_digest()
    assert digest["status"] == "not_implemented"

    added = await server.add_topic("AI agents")
    assert added["status"] == "not_implemented"

    listed = await server.list_topics()
    assert listed["status"] == "not_implemented"


async def test_tools_proxy_to_injected_runtime(monkeypatch):
    class FakeRuntime:
        async def list_topics(self):
            return [{"id": "1", "name": "AI"}]

        async def add_topic(self, name):
            return {"id": "2", "name": name}

        async def remove_topic(self, topic_id):
            return True

        async def get_digest(self):
            return "today's digest"

        async def trigger_analysis(self):
            return "analysis started"

        async def topic_registry_state(self):
            return {"topics": [{"id": "1", "name": "AI"}]}

    monkeypatch.setattr(server, "runtime", FakeRuntime())

    assert await server.get_digest() == "today's digest"
    assert await server.trigger_analysis() == "analysis started"
    assert await server.list_topics() == [{"id": "1", "name": "AI"}]
    assert (await server.add_topic("LLMs"))["name"] == "LLMs"
    assert await server.remove_topic("2") is True


async def test_tool_errors_are_returned_not_raised(monkeypatch):
    class BoomRuntime:
        async def get_digest(self):
            raise ValueError("kaboom")

    monkeypatch.setattr(server, "runtime", BoomRuntime())
    result = await server.get_digest()
    assert result["status"] == "error"
    assert "kaboom" in result["message"]
