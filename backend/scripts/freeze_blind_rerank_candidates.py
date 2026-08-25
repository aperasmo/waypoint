"""Freeze Waypoint's blind production top-5 retrieval candidates.

This is an evaluation-safety utility.

Input:
    tests/rerank_questions_blind_v2.json
    containing only case_id + question.

Output:
    tests/rerank_candidates_blind_v2.json
    containing the exact production top-5 passages for each blind question.

No gold benchmark is opened or imported. The candidate snapshot can then be
reused across repeated reranker runs so reranker stability is measured against
an identical evidence set rather than against repeated retrieval calls.

Run from backend/:
    uv run python -m scripts.freeze_blind_rerank_candidates
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder
from app.retrieval.retriever import retrieve


BACKEND_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BACKEND_DIR / "tests" / "rerank_questions_blind_v2.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "rerank_candidates_blind_v2.json"
EXPECTED_INPUT_SCHEMA = "waypoint-rerank-blind-v1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_blind_input(payload: object) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        raise RuntimeError("Blind input root must be a JSON object.")

    if payload.get("schema") != EXPECTED_INPUT_SCHEMA:
        raise RuntimeError(
            f"Unexpected blind schema: {payload.get('schema')!r}"
        )

    allowed_root = {"schema", "source_question_count", "questions"}
    if set(payload) != allowed_root:
        raise RuntimeError(
            "Blind input root must contain exactly: "
            + ", ".join(sorted(allowed_root))
        )

    questions = payload["questions"]
    if not isinstance(questions, list):
        raise RuntimeError("Blind input questions must be a list.")

    if payload["source_question_count"] != len(questions):
        raise RuntimeError("Blind input question count does not match.")

    seen: set[str] = set()
    validated: list[dict[str, str]] = []

    for index, case in enumerate(questions, start=1):
        if not isinstance(case, dict):
            raise RuntimeError(f"Blind case {index} is not an object.")

        if set(case) != {"case_id", "question"}:
            raise RuntimeError(
                f"Blind case {index} contains fields beyond case_id/question: "
                f"{sorted(case)}"
            )

        case_id = case["case_id"]
        question = case["question"]

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(f"Blind case {index} has invalid case_id.")
        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(f"Blind case {index} has invalid question.")
        if case_id in seen:
            raise RuntimeError(f"Duplicate case_id: {case_id}")

        seen.add(case_id)
        validated.append(
            {"case_id": case_id, "question": question.strip()}
        )

    return validated


async def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Blind input not found: {INPUT_PATH}")

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Output already exists: {OUTPUT_PATH}\n"
            "Delete it deliberately before regenerating the candidate snapshot."
        )

    payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    cases = validate_blind_input(payload)

    factory = get_session_factory()
    embedder = OpenAIEmbedder()
    snapshot_cases: list[dict] = []

    print("Waypoint blind rerank candidate snapshot")
    print("=" * 37)
    print(f"Input:                     {INPUT_PATH}")
    print(f"Questions:                 {len(cases)}")
    print("Retriever top-k:           5")
    print()
    print("Gold labels loaded:        NO")
    print("Freezing production top-5 candidates...")

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
                        f"Expected 5 results for {case['case_id']}; "
                        f"got {len(results)}"
                    )

                candidates: list[dict] = []

                for index, result in enumerate(results, start=1):
                    candidates.append(
                        {
                            "index": index,
                            "section_code": result.section_code,
                            "title": result.title,
                            "chunk_index": result.chunk_index,
                            "chunk_total": result.chunk_total,
                            "text": result.text,
                            "rrf_score": result.score,
                            "vector_rank": result.vector_rank,
                            "text_rank": result.text_rank,
                            "matched_both": result.matched_both,
                        }
                    )

                snapshot_cases.append(
                    {
                        "case_id": case["case_id"],
                        "question": case["question"],
                        "candidates": candidates,
                    }
                )

                print(
                    f"[{number:>2}/{len(cases)}] "
                    f"{case['case_id']} "
                    f"top1={results[0].section_code:<8}"
                )

        output = {
            "schema": "waypoint-rerank-candidates-blind-v1",
            "blind_input_sha256": sha256(INPUT_PATH),
            "retriever_top_k": 5,
            "cases": snapshot_cases,
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
                "Candidate snapshot contains forbidden gold-label fields: "
                + ", ".join(leaked)
            )

        OUTPUT_PATH.write_text(serialised, encoding="utf-8")

        # Re-read and fail closed on the candidate schema.
        verify = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
        if verify.get("schema") != "waypoint-rerank-candidates-blind-v1":
            raise RuntimeError("Unexpected candidate snapshot schema.")
        if len(verify.get("cases", [])) != len(cases):
            raise RuntimeError("Candidate snapshot case count changed.")

        for case in verify["cases"]:
            if set(case) != {"case_id", "question", "candidates"}:
                raise RuntimeError(
                    "Candidate snapshot case contains unexpected fields."
                )
            if len(case["candidates"]) != 5:
                raise RuntimeError(
                    f"{case['case_id']} does not contain exactly 5 candidates."
                )

        print()
        print(f"Snapshot:                  {OUTPUT_PATH}")
        print(f"Blind input SHA256:        {sha256(INPUT_PATH)}")
        print(f"Snapshot SHA256:           {sha256(OUTPUT_PATH)}")
        print(f"Cases frozen:              {len(snapshot_cases)}")
        print("Gold-label fields present: none")
        print("Candidate snapshot:        PASS")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())