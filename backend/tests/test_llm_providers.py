from types import SimpleNamespace

import pytest

from app.llm.bedrock_provider import BedrockProvider
from app.llm.factory import get_llm_provider
from app.llm.openai_provider import OpenAIProvider


class FakeBedrockClient:
    """Minimal fake Bedrock client used to keep tests offline."""

    def converse(self, **kwargs):
        """Return a deterministic Bedrock-like response."""
        return {
            "output": {
                "message": {
                    "content": [
                        {
                            "text": '{"answer":"test"}',
                        }
                    ]
                }
            },
            "usage": {
                "inputTokens": 10,
                "outputTokens": 5,
            },
            "stopReason": "end_turn",
        }

class FakeOpenAICompletions:
    """Fake OpenAI completions API used to keep tests offline."""

    async def create(self, **kwargs):
        """Return a deterministic OpenAI-like response."""

        class Message:
            content = '{"answer":"test"}'

        class Choice:
            message = Message()
            finish_reason = "stop"

        class Usage:
            prompt_tokens = 12
            completion_tokens = 6

        class Response:
            choices = [Choice()]
            usage = Usage()

        return Response()


class FakeOpenAIChat:
    """Expose the completions attribute expected by AsyncOpenAI."""

    def __init__(self):
        self.completions = FakeOpenAICompletions()


class FakeOpenAIClient:
    """Minimal fake OpenAI client for provider unit tests."""

    def __init__(self):
        self.chat = FakeOpenAIChat()

@pytest.mark.asyncio
async def test_openai_provider_generate_normalises_response():
    """OpenAI responses should be converted into Waypoint's common format."""

    provider = OpenAIProvider(
        api_key="test-key",
        model="test-model",
        reasoning_effort="none",
    )

    # Replace the real SDK client after construction so the test stays offline.
    provider._client = FakeOpenAIClient()

    response = await provider.generate(
        LLMRequest(
            system_prompt="Return JSON.",
            messages=[
                LLMMessage(
                    role="user",
                    content="Test question",
                )
            ],
            max_tokens=100,
            temperature=0.0,
            json_mode=True,
        )
    )

    assert response.text == '{"answer":"test"}'
    assert response.input_tokens == 12
    assert response.output_tokens == 6
    assert response.finish_reason == "stop"


def make_settings(**overrides):
    """Create a minimal settings-like object for provider factory tests."""

    values = {
        "llm_provider": "openai",
        "llm_model": "test-model",
        "openai_api_key": "test-key",
        "openai_reasoning_effort": "none",
        "bedrock_region": "ap-southeast-2",

        # Keep test configuration aligned with the Bedrock factory contract.
        "bedrock_input_cost_per_million": 0.30,
        "bedrock_output_cost_per_million": 2.50,
    }

    values.update(overrides)

    return SimpleNamespace(**values)


def test_factory_returns_openai_provider_by_default():
    """OpenAI should remain the default generation provider."""

    settings = make_settings()

    provider = get_llm_provider(settings)

    assert isinstance(provider, OpenAIProvider)


def test_factory_returns_bedrock_provider(monkeypatch):
    """Bedrock should be selected when explicitly configured."""

    fake_client = FakeBedrockClient()

    # Prevent the factory test from constructing a real AWS client.
    monkeypatch.setattr(
        "app.llm.bedrock_provider.boto3.client",
        lambda *args, **kwargs: fake_client,
    )

    settings = make_settings(
        llm_provider="bedrock",
        llm_model="global.amazon.nova-2-lite-v1:0",
    )

    provider = get_llm_provider(settings)

    assert isinstance(provider, BedrockProvider)


def test_factory_normalises_provider_name(monkeypatch):
    """Provider names should tolerate case and surrounding whitespace."""

    fake_client = FakeBedrockClient()

    monkeypatch.setattr(
        "app.llm.bedrock_provider.boto3.client",
        lambda *args, **kwargs: fake_client,
    )

    settings = make_settings(
        llm_provider="  BEDROCK  ",
    )

    provider = get_llm_provider(settings)

    assert isinstance(provider, BedrockProvider)


def test_factory_rejects_unsupported_provider():
    """Unsupported provider names should fail clearly."""

    settings = make_settings(
        llm_provider="unknown",
    )

    with pytest.raises(
        ValueError,
        match="Unsupported LLM provider",
    ):
        get_llm_provider(settings)


from app.llm.base import LLMMessage, LLMRequest


@pytest.mark.asyncio
async def test_bedrock_provider_generate_normalises_response():
    """Bedrock responses should be converted into Waypoint's common format."""

    fake_client = FakeBedrockClient()

    provider = BedrockProvider(
        region="ap-southeast-2",
        model="test-model",
        input_cost_per_million=0.30,
        output_cost_per_million=2.50,
        client=fake_client,
    )

    response = await provider.generate(
        LLMRequest(
            system_prompt="Return JSON.",
            messages=[
                LLMMessage(
                    role="user",
                    content="Test question",
                )
            ],
            max_tokens=100,
            temperature=0.0,
            json_mode=True,
        )
    )

    assert response.text == '{"answer":"test"}'
    assert response.input_tokens == 10
    assert response.output_tokens == 5
    assert response.finish_reason == "end_turn"

    # Verify the estimated cost is calculated from the configured
    # per-million-token rates.
    assert response.input_cost_usd == pytest.approx(0.000003)
    assert response.output_cost_usd == pytest.approx(0.0000125)
    assert response.total_cost_usd == pytest.approx(0.0000155)