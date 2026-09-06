from openai import AsyncOpenAI

from app.llm.base import (
    LLMRequest,
    LLMResponse,
)


class OpenAIProvider:
    """Generate Waypoint responses using OpenAI."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        reasoning_effort: str,
    ) -> None:
        """Initialise the OpenAI client and provider configuration."""
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model
        self._reasoning_effort = reasoning_effort

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Translate Waypoint's standard request into OpenAI's API format."""
        try:
            print(
                f"[START] OpenAI generation model={self._model}"
            )

            # Keep vendor-specific message formatting inside the provider so
            # API routes remain independent of the OpenAI SDK.
            messages = [
                {
                    "role": "system",
                    "content": request.system_prompt,
                },
                *[
                    {
                        "role": message.role,
                        "content": message.content,
                    }
                    for message in request.messages
                ],
            ]

            # Build the request centrally so provider-specific parameters stay
            # isolated from the rest of the application.
            completion = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_completion_tokens=request.max_tokens,
                reasoning_effort=self._reasoning_effort,
                temperature=request.temperature,
                response_format=(
                    {"type": "json_object"}
                    if request.json_mode
                    else None
                ),
            )

            text = (
                completion.choices[0].message.content
                or ""
            )

            usage = completion.usage

            print("[SUCCESS] OpenAI generation complete")

            return LLMResponse(
                text=text,
                input_tokens=(
                    usage.prompt_tokens
                    if usage
                    else None
                ),
                output_tokens=(
                    usage.completion_tokens
                    if usage
                    else None
                ),
                finish_reason=completion.choices[0].finish_reason,
            )

        except Exception as exc:
            print(
                f"[ERROR] OpenAI generation failed: {exc}"
            )
            raise