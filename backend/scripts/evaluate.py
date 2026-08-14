"""Measure retrieval against known-answer questions.

Recall@k asks a narrow question: did the section that answers this appear
in the top k results? It says nothing about whether the final answer would
be correct, only whether the right evidence reached the answer step. That
is the part retrieval controls.
"""

import asyncio
import json
from pathlib import Path

from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder
from app.retrieval.acronyms import expand_acronyms
from app.retrieval.retriever import retrieve

QUESTIONS_PATH = Path(__file__).parent.parent / "tests" / "eval_questions.json"


async def main() -> None:
    cases = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))["questions"]

    factory = get_session_factory()
    embedder = OpenAIEmbedder()

    answerable = [c for c in cases if c["expected_sections"]]
    gaps = [c for c in cases if not c["expected_sections"]]

    hits_at_1 = 0
    hits_at_5 = 0
    misses: list[tuple[str, list[str], list[str]]] = []
    rank1_misses: list[tuple[str, list[str], list[str]]] = []

    async with factory() as session:
        for case in answerable:
            results = await retrieve(session, case["question"], embedder, limit=5)
            retrieved = [r.section_code for r in results]
            expected = set(case["expected_sections"])

            if retrieved and retrieved[0] in expected:
                hits_at_1 += 1
            else:
                rank1_misses.append(
                    (case["question"], case["expected_sections"], retrieved)
                )

            if expected & set(retrieved):
                hits_at_5 += 1
            else:
                misses.append((case["question"], case["expected_sections"], retrieved))

        # Known-gap questions have no right answer. We cannot score them
        # until the ask endpoint decides when to fall back, but printing
        # what retrieval returns shows how convincing the wrong answers look.
        gap_output: list[tuple[str, list[str]]] = []
        for case in gaps:
            results = await retrieve(session, case["question"], embedder, limit=3)
            gap_output.append((case["question"], [r.section_code for r in results]))

    total = len(answerable)
    print(f"\nAnswerable questions: {total}")
    print(f"Recall@1: {hits_at_1}/{total}  ({hits_at_1 / total:.0%})")
    print(f"Recall@5: {hits_at_5}/{total}  ({hits_at_5 / total:.0%})")

    if rank1_misses:
        print(f"\nRank-1 misses ({len(rank1_misses)}):")
        for question, expected, retrieved in rank1_misses:
            print(f"  {question}")
            print(f"    wanted: {', '.join(expected)}")
            print(f"    got:    {', '.join(retrieved[:3])}")

    if misses:
        print(f"\nMissed ({len(misses)}):")
        for question, expected, retrieved in misses:
            expansion = expand_acronyms(question)
            print(f"\n  {question}")
            if expansion.changed:
                print(f"    expanded: {expansion.expanded}")
            print(f"    expected: {', '.join(expected)}")
            print(f"    got:      {', '.join(retrieved) or '(nothing)'}")

    if gap_output:
        print(f"\nKnown gaps ({len(gap_output)}), no correct answer exists:")
        for question, retrieved in gap_output:
            print(f"  {question}")
            print(f"    got: {', '.join(retrieved) or '(nothing)'}")

    await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())