# tests/test_graph.py
from unittest.mock import AsyncMock, patch


STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_graph_has_expected_nodes():
    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            from news.graph import create_graph
            builder = create_graph()

    assert "telegram_pipeline" in builder.nodes
    assert "email_pipeline" in builder.nodes
    assert "merge" in builder.nodes
    assert "sender" in builder.nodes


async def test_full_graph_routes_filtered_signals_to_sender():
    filtered = [{"title": "LangGraph 2.0", "classification": "ai_agent_framework", "summary": "news", "source": "telegram"}]

    mock_tg_pipeline = AsyncMock(return_value={"telegram_offset_id": 200, "filtered_signals": filtered})
    mock_email_pipeline = AsyncMock(return_value={"filtered_signals": []})
    mock_send = AsyncMock(return_value={})

    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            with patch("news.graph.build_telegram_pipeline", return_value=mock_tg_pipeline):
                with patch("news.graph.build_email_pipeline", return_value=mock_email_pipeline):
                    with patch("news.graph.sender_node", mock_send):
                        from langgraph.checkpoint.memory import MemorySaver
                        from news.graph import create_graph

                        graph = create_graph().compile(checkpointer=MemorySaver())
                        result = await graph.ainvoke(
                            STATE_BASE,
                            config={"configurable": {"thread_id": "test"}},
                        )

    assert result["telegram_offset_id"] == 200
    mock_send.assert_called_once()


async def test_sender_skipped_when_no_filtered_signals():
    mock_tg_pipeline = AsyncMock(return_value={"filtered_signals": []})
    mock_email_pipeline = AsyncMock(return_value={"filtered_signals": []})
    mock_send = AsyncMock(return_value={})

    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            with patch("news.graph.build_telegram_pipeline", return_value=mock_tg_pipeline):
                with patch("news.graph.build_email_pipeline", return_value=mock_email_pipeline):
                    with patch("news.graph.sender_node", mock_send):
                        from langgraph.checkpoint.memory import MemorySaver
                        from news.graph import create_graph

                        graph = create_graph().compile(checkpointer=MemorySaver())
                        await graph.ainvoke(
                            STATE_BASE,
                            config={"configurable": {"thread_id": "test-skip"}},
                        )

    mock_send.assert_not_called()


async def test_telegram_collector_resolves_peer_before_fetching_history():
    call_order = []

    async def fake_get_chat(_chat_id):
        call_order.append("get_chat")

    async def fake_history(*_args, **_kwargs):
        call_order.append("get_chat_history")
        return
        yield

    from unittest.mock import MagicMock
    mock_client = MagicMock()
    mock_client.get_chat = fake_get_chat
    mock_client.get_chat_history = fake_history

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=ctx):
        from news.nodes.telegram_collector import telegram_collector_node
        await telegram_collector_node(STATE_BASE)

    assert call_order == ["get_chat", "get_chat_history"]
