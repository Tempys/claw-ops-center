from unittest.mock import AsyncMock, patch


async def test_graph_builder_has_correct_nodes():
    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            from news.graph import build_graph_builder
            builder = build_graph_builder()

    assert "telegram_collector" in builder.nodes
    assert "email_collector" in builder.nodes
    assert "analyze_and_classify" in builder.nodes
    assert "sender" in builder.nodes


async def test_full_graph_produces_analysis_from_both_sources():
    tg_signals = [{"title": "BTC up", "classification": "informational", "summary": "Up 10%", "source": "telegram"}]
    em_signals = [{"title": "Alert", "classification": "informational", "summary": "Volatility", "source": "email"}]

    mock_tg = AsyncMock(return_value={"telegram_offset_id": 200, "signals": tg_signals})
    mock_em = AsyncMock(return_value={"email_last_checked": 9999.0, "signals": em_signals})
    mock_analyze = AsyncMock(return_value={"analysis": "Urgent: BTC up 10%"})
    mock_send = AsyncMock(return_value={})

    with patch("news.nodes.analyzer._client", AsyncMock()):
        with patch("news.nodes.sender._bot", AsyncMock()):
            with patch("news.graph.telegram_collector_node", mock_tg):
                with patch("news.graph.email_collector_node", mock_em):
                    with patch("news.graph.analyze_and_classify_node", mock_analyze):
                        with patch("news.graph.sender_node", mock_send):
                            from langgraph.checkpoint.memory import MemorySaver
                            from news.graph import build_graph_builder

                            graph = build_graph_builder().compile(checkpointer=MemorySaver())
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
    assert result["email_last_checked"] == 9999.0
