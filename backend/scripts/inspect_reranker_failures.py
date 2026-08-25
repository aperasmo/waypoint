"""Inspect the exact retrieved passages for the LLM reranker's failures.

Read-only. Prints the production top-5 passages for the two reranker
regressions and the one remaining rank-1 miss observed in the frozen
25-question benchmark.

Run from backend/:
    uv run python -m scripts.inspect_reranker_failures
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder
from app.retrieval.retriever import retrieve


QUESTIONS_PATH = Path(__file__).parent.parent / "tests" / "eval_questions.json"

TARGET_QUESTIONS = {
    "do I need a police clearance",
    "I have 6 points can I apply for residence",
    (
        "I already have 6 points for SMC but I don't have a job offer "
        "can I apply for residency"
    ),
}


async def main() -> None:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    cases = [
        case
        for case in payload["questions"]
        if case["question"] in TARGET_QUESTIONS
    ]

    missing = TARGET_QUESTIONS - {case["question"] for case in cases}
    if missing:
        raise RuntimeError(
            "Target questions not found in eval_questions.json: "
            + "; ".join(sorted(missing))
        )

    factory = get_session_factory()
    embedder = OpenAIEmbedder()

    try:
        async with factory() as session:
            print("Waypoint reranker-failure passage inspection")
            print("=" * 45)

            for case in cases:
                question = case["question"]
                results = await retrieve(
                    session,
                    question,
                    embedder,
                    limit=5,
                )

                print()
                print("=" * 88)
                print(f"Question: {question}")
                print(
                    "Expected section(s): "
                    + ", ".join(case["expected_sections"])
                )
                print("=" * 88)

                for rank, result in enumerate(results, start=1):
                    expected = (
                        result.section_code in set(case["expected_sections"])
                    )
                    marker = "*" if expected else " "

                    print()
                    print(
                        f"{marker}Candidate {rank}: "
                        f"{result.section_code} "
                        f"chunk {result.chunk_index + 1}/{result.chunk_total}"
                    )
                    print(f"Title: {result.title}")
                    print(
                        f"RRF: {result.score:.6f} | "
                        f"vector={result.vector_rank or '-'} | "
                        f"text={result.text_rank or '-'} | "
                        f"both={'yes' if result.matched_both else 'no'}"
                    )
                    print("-" * 88)
                    print(result.text)
                    print("-" * 88)

            print()
            print(
                "Read-only inspection complete. "
                "No corpus or database rows were changed."
            )

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())