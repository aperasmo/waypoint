import asyncio

import boto3

from app.llm.base import (
    LLMRequest,
    LLMResponse,
)


class BedrockProvider:
    """Generate Waypoint responses using Amazon Bedrock."""

    def __init__(
        self,
        *,
        region: str,
        model: str,
        input_cost_per_million: float,
        output_cost_per_million: float,
        client=None,
    ) -> None:
        """Initialise the Bedrock provider and optionally accept a test client."""

        self._model = model
        self._input_cost_per_million = input_cost_per_million
        self._output_cost_per_million = output_cost_per_million

        # In production, create the real Bedrock Runtime client.
        # Tests can inject a fake client so they remain offline and deterministic.
        self._client = client or boto3.client(
            "bedrock-runtime",
            region_name=region,
        )

    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """Translate Waypoint's standard request into Bedrock Converse format."""
        try:
            print(
                f"[START] Bedrock generation model={self._model}"
            )

            system_prompt = request.system_prompt

            # Bedrock models do not all expose the same native JSON-output
            # controls. Waypoint therefore reinforces JSON output in the
            # system prompt and still validates the returned payload later.
            if request.json_mode:
                system_prompt += (
                    "\n\nReturn only a valid JSON object. "
                    "Do not include Markdown or explanatory text "
                    "outside the JSON object."
                )

            # Convert Waypoint's provider-neutral message structure into the
            # content-block format expected by the Bedrock Converse API.
            messages = [
                {
                    "role": message.role,
                    "content": [
                        {
                            "text": message.content,
                        }
                    ],
                }
                for message in request.messages
            ]

            # boto3 is synchronous. Run the network request in a worker thread
            # so FastAPI's async event loop is not blocked while Bedrock responds.
            response = await asyncio.to_thread(
                self._client.converse,
                modelId=self._model,
                system=[
                    {
                        "text": system_prompt,
                    }
                ],
                messages=messages,
                inferenceConfig={
                    "maxTokens": request.max_tokens,
                    "temperature": request.temperature,
                },
            )

            # Normalise Bedrock's response shape into Waypoint's common
            # LLMResponse contract.
            text = (
                response["output"]["message"]["content"][0]["text"]
            )

            usage = response.get("usage", {})

            input_tokens = usage.get("inputTokens")
            output_tokens = usage.get("outputTokens")

            # Estimate request cost from the token usage returned by Bedrock.
            # Rates are configuration values so pricing changes do not require
            # application-code changes.
            input_cost_usd = (
                input_tokens / 1_000_000 * self._input_cost_per_million
                if input_tokens is not None
                else None
            )

            output_cost_usd = (
                output_tokens / 1_000_000 * self._output_cost_per_million
                if output_tokens is not None
                else None
            )

            total_cost_usd = (
                input_cost_usd + output_cost_usd
                if input_cost_usd is not None
                and output_cost_usd is not None
                else None
            )

            if total_cost_usd is not None:
                print(
                    "[SUCCESS] Bedrock generation complete "
                    f"input_tokens={input_tokens} "
                    f"output_tokens={output_tokens} "
                    f"estimated_cost_usd={total_cost_usd:.6f}"
                )
            else:
                print(
                    "[SUCCESS] Bedrock generation complete "
                    "cost unavailable"
                )

            return LLMResponse(
                text=text,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                finish_reason=response.get("stopReason"),
                input_cost_usd=input_cost_usd,
                output_cost_usd=output_cost_usd,
            )

        except Exception as exc:
            print(
                f"[ERROR] Bedrock generation failed: {exc}"
            )
            raise