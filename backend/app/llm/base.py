from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class LLMMessage:
    """Provider-neutral chat message used by Waypoint."""

    role: str
    content: str


@dataclass(frozen=True)
class LLMRequest:
    """Common generation request shared by all LLM providers."""

    system_prompt: str
    messages: list[LLMMessage]
    max_tokens: int = 800
    temperature: float = 0.0

    # Providers translate this intent into their own structured-output
    # mechanism. Waypoint still validates the returned JSON afterwards.
    json_mode: bool = False


@dataclass(frozen=True)
class LLMResponse:
    """Normalised response returned by every provider implementation."""

    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    finish_reason: str | None = None

    # Estimated provider cost in USD for this generation request.
    input_cost_usd: float | None = None
    output_cost_usd: float | None = None

    @property
    def total_cost_usd(self) -> float | None:
        """Return the combined estimated cost when both parts are available."""

        if (
            self.input_cost_usd is None
            or self.output_cost_usd is None
        ):
            return None

        return self.input_cost_usd + self.output_cost_usd


class LLMProvider(Protocol):
    """Interface that every Waypoint LLM provider must implement."""

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Generate a response using the provider-specific API."""
        ...