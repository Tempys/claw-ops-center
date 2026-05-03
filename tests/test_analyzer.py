from unittest.mock import AsyncMock, MagicMock, patch

STATE = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [
        {"title": "BTC surges", "classification": "informational", "summary": "BTC up 15%", "source": "telegram"},
        {"title": "Volatility alert", "classification": "informational", "summary": "VIX spike", "source": "email"},
    ],
    "analysis": "",
}


async def test_returns_llm_analysis_text():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="URGENT: BTC up 15%. VIX spike warrants monitoring.")]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("openclaw.nodes.analyzer._client", mock_client):
        from openclaw.nodes.analyzer import analyze_and_classify_node
        result = await analyze_and_classify_node(STATE)

    assert result["analysis"] == "URGENT: BTC up 15%. VIX spike warrants monitoring."


async def test_prompt_includes_all_signals():
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text="Summary")]
    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(return_value=mock_response)

    with patch("openclaw.nodes.analyzer._client", mock_client):
        from openclaw.nodes.analyzer import analyze_and_classify_node
        await analyze_and_classify_node(STATE)

    call_kwargs = mock_client.messages.create.call_args.kwargs
    prompt = call_kwargs["messages"][0]["content"]
    assert "BTC surges" in prompt
    assert "Volatility alert" in prompt
    assert "telegram" in prompt.lower()
    assert "email" in prompt.lower()
