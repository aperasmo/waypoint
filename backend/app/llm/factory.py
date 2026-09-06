from app.config import Settings
from app.llm.base import LLMProvider
from app.llm.bedrock_provider import BedrockProvider
from app.llm.openai_provider import OpenAIProvider


def get_llm_provider(
    settings: Settings,
) -> LLMProvider:
    """Return the configured LLM provider for Waypoint."""

    # Normalise the configured provider name so environment values such as
    # "OpenAI", "openai", or " OPENAI " behave consistently.
    provider_name = settings.llm_provider.strip().lower()

    # Keep provider-specific construction in one place so API routes do not
    # depend on vendor SDKs, credentials, or configuration details.
    if provider_name == "openai":
        return OpenAIProvider(
            api_key=settings.openai_api_key,
            model=settings.llm_model,
            reasoning_effort=settings.openai_reasoning_effort,
        )

    if provider_name == "bedrock":
        return BedrockProvider(
            region=settings.bedrock_region,
            model=settings.llm_model,
            input_cost_per_million=(
                settings.bedrock_input_cost_per_million
            ),
            output_cost_per_million=(
                settings.bedrock_output_cost_per_million
            ),
        )

    # Fail early for unsupported configuration rather than allowing an
    # invalid provider name to surface later during a user request.
    raise ValueError(
        f"Unsupported LLM provider: {settings.llm_provider}"
    )