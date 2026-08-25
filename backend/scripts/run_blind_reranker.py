"""Blind Waypoint top-5 reranking.

This process has no access to gold labels.

Input schema:
    {
      "schema": "waypoint-rerank-blind-v1",
      "source_question_count": N,
      "questions": [
        {"case_id": "...", "question": "..."}
      ]
    }

Output contains only predictions and retrieval observations. It never reads
expected_sections or any gold benchmark.

Run from backend/:
    uv run python -m scripts.run_blind_reranker
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder
from app.retrieval.retriever import retrieve


BACKEND_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BACKEND_DIR / "tests" / "rerank_questions_blind_v2.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "rerank_predictions_blind_v2.json"

EXPECTED_SCHEMA = "waypoint-rerank-blind-v1"

RERANK_SYSTEM_PROMPT = """You are a retrieval reranker for the New Zealand
Immigration Operational Manual.

You are given one user question and exactly five passages already retrieved
from the manual.

Your task is only to identify which passage most directly contains the
published rule needed to answer the question.

Rules:
- Do not answer the immigration question.
- Do not use outside knowledge.
- Judge only from the supplied passages.
- Prefer the passage containing the specific operative rule over a broader
  overview, adjacent rule, definition, or merely related topic.
- If multiple passages are from the same section, choose the passage whose
  text most directly addresses the question.
- Return JSON only in this exact shape:
  {"best_index": 1}
- best_index must be an integer from 1 to 5.
"""


class RerankChoice(BaseModel):
    best_index: int = Field(ge=1, le=5)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_blind_input(payload: object) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        raise RuntimeError("Blind input root must be a JSON object.")

    allowed_root = {"schema", "source_question_count", "questions"}
    unexpected_root = set(payload) - allowed_root
    if unexpected_root:
        raise RuntimeError(
            "Blind input contains unexpected root fields: "
            + ", ".join(sorted(unexpected_root))
        )

    if payload.get("schema") != EXPECTED_SCHEMA:
        raise RuntimeError(
            f"Unexpected blind schema: {payload.get('schema')!r}"
        )

    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("Blind input 'questions' must be a list.")

    declared_count = payload.get("source_question_count")
    if declared_count != len(questions):
        raise RuntimeError(
            f"Declared question count {declared_count!r} does not match "
            f"actual count {len(questions)}."
        )

    seen_ids: set[str] = set()
    validated: list[dict[str, str]] = []

    for index, case in enumerate(questions, start=1):
        if not isinstance(case, dict):
            raise RuntimeError(f"Blind case {index} is not an object.")

        # This is the key leakage guard. No gold fields or other metadata
        # are permitted in the reranker's input.
        if set(case) != {"case_id", "question"}:
            raise RuntimeError(
                f"Blind case {index} must contain exactly "
                "'case_id' and 'question'. "
                f"Found: {sorted(case)}"
            )

        case_id = case["case_id"]
        question = case["question"]

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(f"Blind case {index} has invalid case_id.")
        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(f"Blind case {index} has invalid question.")
        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate case_id: {case_id}")

        seen_ids.add(case_id)
        validated.append(
            {
                "case_id": case_id,
                "question": question.strip(),
            }
        )

    return validated


def format_candidates(results) -> str:
    blocks: list[str] = []

    for index, result in enumerate(results, start=1):
        blocks.append(
            "\n".join(
                [
                    f"Candidate {index}",
                    f"Section: {result.section_code}",
                    f"Title: {result.title}",
                    (
                        f"Chunk: {result.chunk_index + 1}"
                        f"/{result.chunk_total}"
                    ),
                    "Passage:",
                    result.text,
                ]
            )
        )

    return "\n\n---\n\n".join(blocks)


async def choose_best(
    client: AsyncOpenAI,
    *,
    model: str,
    max_tokens: int,
    reasoning_effort: str,
    question: str,
    results,
) -> int:
    completion = await client.chat.completions.create(
        model=model,
        max_completion_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": RERANK_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Retrieved passages:\n\n"
                    f"{format_candidates(results)}"
                ),
            },
        ],
    )

    raw = completion.choices[0].message.content or "{}"

    try:
        parsed = json.loads(raw)
        choice = RerankChoice.model_validate(parsed)
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(
            f"Malformed reranker output for case question {question!r}: "
            f"{raw!r}"
        ) from exc

    return choice.best_index


async def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Blind input not found: {INPUT_PATH}")

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Output already exists: {OUTPUT_PATH}\n"
            "Delete it deliberately before rerunning the blind prediction."
        )

    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    cases = validate_blind_input(payload)

    settings = get_settings()
    factory = get_session_factory()
    embedder = OpenAIEmbedder()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    predictions: list[dict] = []

    print("Waypoint blind top-5 reranker")
    print("=" * 29)
    print(f"Input:                     {INPUT_PATH}")
    print(f"Questions:                 {len(cases)}")
    print(f"Retriever top-k:           5")
    print(f"Reranker model:            {settings.answer_model}")
    print(
        f"Reasoning effort:          "
        f"{settings.answer_reasoning_effort}"
    )
    print(
        f"Max completion tokens:     "
        f"{settings.answer_max_tokens}"
    )
    print()
    print("Gold labels loaded:        NO")
    print("Running blind predictions...")

    try:
        async with factory() as session:
            for number, case in enumerate(cases, start=1):
                results = await retrieve(
                    session,
                    case["question"],
                    embedder,
                    limit=5,
                )

                if len(results) != 5:
                    raise RuntimeError(
                        f"Expected 5 retrieval results for "
                        f"{case['case_id']}; got {len(results)}"
                    )

                best_index = await choose_best(
                    client,
                    model=settings.answer_model,
                    max_tokens=settings.answer_max_tokens,
                    reasoning_effort=settings.answer_reasoning_effort,
                    question=case["question"],
                    results=results,
                )

                chosen = results[best_index - 1]

                predictions.append(
                    {
                        "case_id": case["case_id"],
                        "question": case["question"],
                        "production_top1_section": results[0].section_code,
                        "retrieved_sections": [
                            result.section_code for result in results
                        ],
                        "chosen_index": best_index,
                        "chosen_section": chosen.section_code,
                    }
                )

                print(
                    f"[{number:>2}/{len(cases)}] "
                    f"{case['case_id']} "
                    f"production={results[0].section_code:<8} "
                    f"chosen={chosen.section_code:<8}"
                )

        output = {
            "schema": "waypoint-rerank-predictions-v1",
            "blind_input_sha256": sha256(INPUT_PATH),
            "model": settings.answer_model,
            "reasoning_effort": settings.answer_reasoning_effort,
            "max_completion_tokens": settings.answer_max_tokens,
            "retriever_top_k": 5,
            "predictions": predictions,
        }

        serialised = json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ) + "\n"

        # Prediction output must not contain gold-label field names either.
        forbidden = (
            '"expected_sections"',
            '"expected_section"',
            '"gold"',
        )
        lowered = serialised.lower()
        leaked = [
            token
            for token in forbidden
            if token.lower() in lowered
        ]
        if leaked:
            raise RuntimeError(
                "Prediction output unexpectedly contains gold-label fields: "
                + ", ".join(leaked)
            )

        OUTPUT_PATH.write_text(serialised, encoding="utf-8")

        print()
        print(f"Predictions:               {OUTPUT_PATH}")
        print(f"Blind input SHA256:        {sha256(INPUT_PATH)}")
        print(f"Prediction count:          {len(predictions)}")
        print("Gold-label fields present: none")
        print("Blind reranking:           PASS")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())