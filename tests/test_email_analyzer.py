# tests/test_email_analyzer.py
import json
from unittest.mock import AsyncMock, MagicMock, patch


def _make_openai_response(text: str) -> MagicMock:
    response = MagicMock()
    response.choices = [MagicMock()]
    response.choices[0].message.content = text
    return response


STATE_BASE = {
    "telegram_offset_id": 0,
    "telegram_raw_signals": [],
    "telegram_seen_hashes": [],
    "email_last_checked": 0.0,
    "email_raw_signals": [],
    "email_seen_hashes": [],
    "filtered_signals": [],
}


async def test_email_analyze_node_classifies_signals():
    signals = [
        {"url": "https://mail.example.com/autogen", "title": "AutoGen v0.5 newsletter", "classification": "other", "summary": "New multi-agent release with tool-use", "source": "email"},
        {"url": "https://mail.example.com/sale", "title": "50% off our new course!", "classification": "other", "summary": "Limited time promotion", "source": "email"},
    ]
    classify_json = json.dumps([
        {"index": 1, "classification": "ai_agent_framework"},
        {"index": 2, "classification": "other"},
    ])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_make_openai_response(classify_json))

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.email_analyzer import email_analyze_node
        result = await email_analyze_node({**STATE_BASE, "email_raw_signals": signals})

    assert len(result["filtered_signals"]) == 2
    assert result["filtered_signals"][0]["classification"] == "ai_agent_framework"
    assert result["filtered_signals"][1]["classification"] == "other"


async def test_email_analyze_node_classifies_promotional_as_other():
    signals = [
        {"url": "https://mail.example.com/sale", "title": "Sale ends tonight", "classification": "other", "summary": "Buy now", "source": "email"},
    ]
    classify_json = json.dumps([{"index": 1, "classification": "other"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_make_openai_response(classify_json))

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.email_analyzer import email_analyze_node
        result = await email_analyze_node({**STATE_BASE, "email_raw_signals": signals})

    assert len(result["filtered_signals"]) == 1
    assert result["filtered_signals"][0]["classification"] == "other"


async def test_email_analyze_node_uses_email_system_prompt():
    signals = [
        {"url": "https://mail.example.com/lora", "title": "LLM fine-tuning guide", "classification": "other", "summary": "Step-by-step LoRA tutorial", "source": "email"},
    ]
    classify_json = json.dumps([{"index": 1, "classification": "llm_finetuning"}])
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(return_value=_make_openai_response(classify_json))

    with patch("news.nodes.analyzer._client", mock_client):
        from news.nodes.email_analyzer import email_analyze_node, _EMAIL_SYSTEM
        await email_analyze_node({**STATE_BASE, "email_raw_signals": signals})

    call_args = mock_client.chat.completions.create.call_args
    system_msg = call_args.kwargs["messages"][0]["content"]
    assert system_msg == _EMAIL_SYSTEM
