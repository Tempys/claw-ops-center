import json
from unittest.mock import AsyncMock, MagicMock, patch


def _make_openai_response(text: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    return response


# ── _classify_batch tests ───────────────────────────────────────────────────


async def test_classify_pass_updates_signal_classification():
    classify_json = json.dumps(
        [
            {"index": 1, "classification": "ai_agent_framework"},
            {"index": 2, "classification": "other"},
        ]
    )
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch

        signals = [
            {
                "url": "https://github.com/langchain-ai/langgraph",
                "classification": "other",
            },
            {"url": "https://coinmarketcap.com/btc", "classification": "other"},
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
            {
                "url": "https://github.com/langchain-ai/langgraph",
                "classification": "other",
            },
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
            {"url": "https://github.com/some/repo", "classification": "other"},
        ]
        result = await _classify_batch(signals, "test prompt")

    assert result[0]["classification"] == "other"


async def test_classify_pass_coerces_error_classification_to_other():
    classify_json = json.dumps([{"index": 1, "classification": "error"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_openai_response(classify_json)
    )

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.analyzer import _classify_batch

        signals = [
            {"url": "https://github.com/some/repo", "classification": "other"},
        ]
        result = await _classify_batch(signals, "test prompt")

    assert result[0]["classification"] == "other"
