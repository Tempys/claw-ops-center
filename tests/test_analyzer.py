import json
from unittest.mock import AsyncMock, MagicMock, patch


def _make_openai_response(text: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    return response


# ── _classify_batch tests ───────────────────────────────────────────────────

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
        result = await _classify_batch(signals, "test prompt")

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
        result = await _classify_batch(signals, "test prompt")

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
        result = await _classify_batch(signals, "test prompt")

    assert result[0]["classification"] == "other"


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
        result = await _classify_batch(signals, "test prompt")

    mock_client.chat.completions.create.assert_not_called()
    assert result[0]["classification"] == "error"


async def test_classify_pass_coerces_error_classification_to_other():
    classify_json = json.dumps([{"index": 1, "classification": "error"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch
        signals = [
            {"title": "Some signal", "classification": "other", "summary": "content", "source": "telegram"},
        ]
        result = await _classify_batch(signals, "test prompt")

    assert result[0]["classification"] == "other"
