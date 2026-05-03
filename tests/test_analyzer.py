import json
from unittest.mock import AsyncMock, MagicMock, patch


def _make_openai_response(text: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    return response


STATE = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [
        {"title": "LangGraph 2.0 drops", "classification": "other", "summary": "Major LangGraph release with new features", "source": "telegram"},
        {"title": "BTC price update", "classification": "other", "summary": "BTC up 5%", "source": "telegram"},
    ],
    "analysis": "",
}

STATE_WITH_ERROR = {
    "telegram_offset_id": 0,
    "email_last_checked": 0.0,
    "signals": [
        {"title": "Collector failed", "classification": "error", "summary": "connection refused", "source": "telegram"},
        {"title": "AutoGen workshop", "classification": "other", "summary": "New AutoGen tutorial repo", "source": "telegram"},
    ],
    "analysis": "",
}


async def test_returns_analysis_text():
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        _make_openai_response(classify_json),
        _make_openai_response("Dev-tool digest: LangGraph 2.0 released. BTC up 5%."),
    ])

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import analyze_and_classify_node
        result = await analyze_and_classify_node(STATE)

    assert result["analysis"] == "Dev-tool digest: LangGraph 2.0 released. BTC up 5%."


async def test_classify_pass_updates_signal_classification():
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "LangGraph 2.0 drops", "classification": "other", "summary": "Major LangGraph release", "source": "telegram"},
            {"title": "BTC price update", "classification": "other", "summary": "BTC up 5%", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    assert result[0]["classification"] == "ai_agent_framework"
    assert result[1]["classification"] == "other"


async def test_classify_pass_falls_back_to_other_on_invalid_json():
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("not valid json {{{{")
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "LangGraph 2.0 drops", "classification": "other", "summary": "Major LangGraph release", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    assert result[0]["classification"] == "other"


async def test_classify_pass_coerces_unknown_category_to_other():
    classify_json = json.dumps([{"index": 1, "classification": "definitely_not_valid"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "Some signal", "classification": "other", "summary": "content", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    assert result[0]["classification"] == "other"


async def test_error_signals_bypass_classify_pass():
    # STATE_WITH_ERROR has one error + one non-error signal.
    # _classify_batch is called for the non-error signal (1 classify call),
    # then the digest call is made — so two responses are needed.
    classify_json = json.dumps([{"index": 1, "classification": "other"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        _make_openai_response(classify_json),
        _make_openai_response("Digest text"),
    ])

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import analyze_and_classify_node
        result = await analyze_and_classify_node(STATE_WITH_ERROR)

    assert mock_client.chat.completions.create.called
    assert "analysis" in result


async def test_error_only_batch_skips_classify_call():
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response("Digest text")
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "Collector failed", "classification": "error", "summary": "err", "source": "telegram"},
        ]
        result = await _classify_batch(signals)

    mock_client.chat.completions.create.assert_not_called()
    assert result[0]["classification"] == "error"


async def test_digest_prompt_includes_classification_labels():
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=[
        _make_openai_response(classify_json),
        _make_openai_response("Digest"),
    ])

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import analyze_and_classify_node
        await analyze_and_classify_node(STATE)

    digest_call = mock_client.chat.completions.create.call_args_list[1]
    prompt = digest_call.kwargs["messages"][1]["content"]
    assert "ai_agent_framework" in prompt
    assert "other" in prompt
