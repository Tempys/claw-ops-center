from unittest.mock import AsyncMock, MagicMock, patch


async def test_graph_builder_has_correct_nodes():
    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            from news.graph import create_graph
            builder = create_graph()

    assert "telegram_collector" in builder.nodes
    assert "analyze_and_classify" in builder.nodes
    assert "sender" in builder.nodes


async def test_full_graph_produces_analysis_from_telegram():
    tg_signals = [{"title": "BTC up", "classification": "other", "summary": "Up 10%", "source": "telegram"}]

    mock_tg = AsyncMock(return_value={"telegram_offset_id": 200, "signals": tg_signals})
    mock_analyze = AsyncMock(return_value={"analysis": "Urgent: BTC up 10%"})
    mock_send = AsyncMock(return_value={})

    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            with patch("news.graph.telegram_collector_node", mock_tg):
                with patch("news.graph.analyze_and_classify_node", mock_analyze):
                    with patch("news.graph.sender_node", mock_send):
                        from langgraph.checkpoint.memory import MemorySaver
                        from news.graph import create_graph

                        graph = create_graph().compile(checkpointer=MemorySaver())
                        initial = {
                            "telegram_offset_id": 0,
                            "email_last_checked": 0.0,
                            "signals": [],
                            "analysis": "",
                        }
                        result = await graph.ainvoke(
                            initial,
                            config={"configurable": {"thread_id": "test"}},
                        )

    assert result["analysis"] == "Urgent: BTC up 10%"
    assert result["telegram_offset_id"] == 200


async def test_telegram_collector_resolves_peer_before_fetching_history():
    """get_chat must be called before get_chat_history to warm pyrogram's peer cache."""
    call_order = []

    async def fake_get_chat(_chat_id):
        call_order.append("get_chat")

    async def fake_history(*_args, **_kwargs):
        call_order.append("get_chat_history")
        return
        yield

    mock_client = MagicMock()
    mock_client.get_chat = fake_get_chat
    mock_client.get_chat_history = fake_history

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=mock_client)
    ctx.__aexit__ = AsyncMock(return_value=False)

    with patch("news.nodes.telegram_collector.make_client", return_value=ctx):
        from news.nodes.telegram_collector import telegram_collector_node
        await telegram_collector_node({"telegram_offset_id": 0, "signals": []})

    assert call_order == ["get_chat", "get_chat_history"]
