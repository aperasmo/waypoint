"""Measure Waypoint LLM reranker stability on a frozen candidate snapshot.

This process is blind to gold labels.

It reads:
    tests/rerank_candidates_blind_v2.json

It does NOT:
- call retrieval;
- open eval_questions*.json;
- load expected_sections;
- modify corpus or database state.

Each case is reranked repeatedly against the exact same five frozen passages.
The script reports unanimous vs variable choices and writes a stability artifact.

Run from backend/:
    uv run python -m scripts.measure_reranker_stability

Optional:
    uv run python -m scripts.measure_reranker_stability --runs 5
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import ValidationError

from app.config import get_settings
from scripts.run_blind_reranker import RERANK_SYSTEM_PROMPT, RerankChoice


BACKEND_DIR = Path(__file__).resolve().parent.parent
SNAPSHOT_PATH = BACKEND_DIR / "tests" / "rerank_candidates_blind_v2.json"
DEFAULT_OUTPUT = BACKEND_DIR / "tests" / "rerank_stability_blind_v2.json"
EXPECTED_SCHEMA = "waypoint-rerank-candidates-blind-v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_snapshot(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise RuntimeError("Candidate snapshot root must be a JSON object.")

    allowed_root = {
        "schema",
        "blind_input_sha256",
        "retriever_top_k",
        "cases",
    }
    if set(payload) != allowed_root:
        raise RuntimeError(
            "Candidate snapshot root contains unexpected fields: "
            + ", ".join(sorted(set(payload) - allowed_root))
        )

    if payload.get("schema") != EXPECTED_SCHEMA:
        raise RuntimeError(
            f"Unexpected candidate snapshot schema: {payload.get('schema')!r}"
        )

    if payload.get("retriever_top_k") != 5:
        raise RuntimeError(
            f"Expected retriever_top_k=5, got {payload.get('retriever_top_k')!r}"
        )

    cases = payload.get("cases")
    if not isinstance(cases, list):
        raise RuntimeError("Candidate snapshot cases must be a list.")

    seen_ids: set[str] = set()
    validated: list[dict] = []

    for case_number, case in enumerate(cases, start=1):
        if not isinstance(case, dict):
            raise RuntimeError(f"Snapshot case {case_number} is not an object.")

        if set(case) != {"case_id", "question", "candidates"}:
            raise RuntimeError(
                f"Snapshot case {case_number} contains unexpected fields: "
                f"{sorted(case)}"
            )

        case_id = case["case_id"]
        question = case["question"]
        candidates = case["candidates"]

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(f"Snapshot case {case_number} has invalid case_id.")
        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate case_id: {case_id}")
        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(f"Snapshot case {case_number} has invalid question.")
        if not isinstance(candidates, list) or len(candidates) != 5:
            raise RuntimeError(
                f"Snapshot case {case_id} must contain exactly 5 candidates."
            )

        expected_candidate_fields = {
            "index",
            "section_code",
            "title",
            "chunk_index",
            "chunk_total",
            "text",
            "rrf_score",
            "vector_rank",
            "text_rank",
            "matched_both",
        }

        for index, candidate in enumerate(candidates, start=1):
            if not isinstance(candidate, dict):
                raise RuntimeError(
                    f"{case_id} candidate {index} is not an object."
                )
            if set(candidate) != expected_candidate_fields:
                raise RuntimeError(
                    f"{case_id} candidate {index} contains unexpected fields."
                )
            if candidate["index"] != index:
                raise RuntimeError(
                    f"{case_id} candidate index mismatch at position {index}."
                )

        seen_ids.add(case_id)
        validated.append(
            {
                "case_id": case_id,
                "question": question.strip(),
                "candidates": candidates,
            }
        )

    return validated


def format_candidates(candidates: list[dict]) -> str:
    blocks: list[str] = []

    for candidate in candidates:
        blocks.append(
            "\n".join(
                [
                    f"Candidate {candidate['index']}",
                    f"Section: {candidate['section_code']}",
                    f"Title: {candidate['title']}",
                    (
                        f"Chunk: {candidate['chunk_index'] + 1}"
                        f"/{candidate['chunk_total']}"
                    ),
                    "Passage:",
                    candidate["text"],
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
    candidates: list[dict],
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
                    f"{format_candidates(candidates)}"
                ),
            },
        ],
    )

    raw = completion.choices[0].message.content or "{}"

    try:
        parsed = json.loads(raw)
        return RerankChoice.model_validate(parsed).best_index
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(
            f"Malformed reranker output for {question!r}: {raw!r}"
        ) from exc


async def main(runs: int, output_path: Path) -> None:
    if runs < 2:
        raise SystemExit("--runs must be at least 2 for a stability test.")

    if not SNAPSHOT_PATH.exists():
        raise SystemExit(f"Candidate snapshot not found: {SNAPSHOT_PATH}")

    if output_path.exists():
        raise SystemExit(
            f"Output already exists: {output_path}\n"
            "Delete it deliberately before rerunning the stability test."
        )

    payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    cases = validate_snapshot(payload)

    settings = get_settings()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    print("Waypoint blind reranker stability")
    print("=" * 33)
    print(f"Snapshot:                  {SNAPSHOT_PATH}")
    print(f"Snapshot SHA256:           {sha256(SNAPSHOT_PATH)}")
    print(f"Cases:                     {len(cases)}")
    print(f"Runs per case:             {runs}")
    print(f"Reranker model:            {settings.answer_model}")
    print(f"Reasoning effort:          {settings.answer_reasoning_effort}")
    print(f"Max completion tokens:     {settings.answer_max_tokens}")
    print()
    print("Retrieval calls:           NONE")
    print("Gold labels loaded:        NO")
    print("Running repeated reranks on frozen passages...")

    case_results: list[dict] = []

    for case_number, case in enumerate(cases, start=1):
        choices: list[int] = []

        for _ in range(runs):
            choice = await choose_best(
                client,
                model=settings.answer_model,
                max_tokens=settings.answer_max_tokens,
                reasoning_effort=settings.answer_reasoning_effort,
                question=case["question"],
                candidates=case["candidates"],
            )
            choices.append(choice)

        sections = [
            case["candidates"][choice - 1]["section_code"]
            for choice in choices
        ]

        index_counts = Counter(choices)
        section_counts = Counter(sections)
        unanimous_index = len(index_counts) == 1
        unanimous_section = len(section_counts) == 1

        case_results.append(
            {
                "case_id": case["case_id"],
                "question": case["question"],
                "chosen_indices": choices,
                "chosen_sections": sections,
                "unanimous_index": unanimous_index,
                "unanimous_section": unanimous_section,
                "index_counts": {
                    str(index): count
                    for index, count in sorted(index_counts.items())
                },
                "section_counts": dict(sorted(section_counts.items())),
            }
        )

        status = "STABLE" if unanimous_index else "VARIABLE"
        display_choices = ",".join(str(choice) for choice in choices)
        display_sections = ",".join(sections)

        print(
            f"[{case_number:>2}/{len(cases)}] "
            f"{status:<8} {case['case_id']} "
            f"choices={display_choices:<9} "
            f"sections={display_sections}"
        )

    unanimous_index_count = sum(
        1 for result in case_results if result["unanimous_index"]
    )
    unanimous_section_count = sum(
        1 for result in case_results if result["unanimous_section"]
    )
    variable_results = [
        result
        for result in case_results
        if not result["unanimous_index"]
    ]

    output = {
        "schema": "waypoint-rerank-stability-blind-v1",
        "candidate_snapshot_sha256": sha256(SNAPSHOT_PATH),
        "model": settings.answer_model,
        "reasoning_effort": settings.answer_reasoning_effort,
        "max_completion_tokens": settings.answer_max_tokens,
        "temperature": 0,
        "runs_per_case": runs,
        "case_count": len(cases),
        "results": case_results,
    }

    serialised = json.dumps(
        output,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    forbidden = (
        '"expected_sections"',
        '"expected_section"',
        '"gold"',
    )
    lowered = serialised.lower()
    leaked = [
        token for token in forbidden if token.lower() in lowered
    ]
    if leaked:
        raise RuntimeError(
            "Stability output contains forbidden gold-label fields: "
            + ", ".join(leaked)
        )

    output_path.write_text(serialised, encoding="utf-8")

    print()
    print("Stability summary")
    print("-" * 76)
    print(
        f"Unanimous exact choice:    "
        f"{unanimous_index_count}/{len(cases)} "
        f"({unanimous_index_count / len(cases):.0%})"
    )
    print(
        f"Unanimous section choice:  "
        f"{unanimous_section_count}/{len(cases)} "
        f"({unanimous_section_count / len(cases):.0%})"
    )
    print(f"Variable cases:            {len(variable_results)}")

    if variable_results:
        print()
        print("Variable cases")
        print("-" * 76)
        for result in variable_results:
            print(f"{result['case_id']}  {result['question']}")
            print(
                f"    indices:  "
                f"{', '.join(map(str, result['chosen_indices']))}"
            )
            print(
                f"    sections: "
                f"{', '.join(result['chosen_sections'])}"
            )

    print()
    print(f"Output:                    {output_path}")
    print(f"Output SHA256:             {sha256(output_path)}")
    print("Gold-label fields present: none")
    print("Blind stability test:      PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Measure repeated LLM reranking against one frozen candidate set."
        )
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Reranker calls per case (default: 3).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()

    asyncio.run(main(args.runs, args.output))