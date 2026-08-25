"""Diagnose Waypoint's production rank-1 retrieval misses.

Read-only. Uses the same production vector, FTS and RRF components.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder
from app.retrieval.acronyms import expand_acronyms
from app.retrieval.retriever import (
    CANDIDATES_PER_LEG,
    RRF_K,
    _fuse,
    _text_candidates,
    _vector_candidates,
)

QUESTIONS_PATH = Path(__file__).parent.parent / "tests" / "eval_questions.json"


def section_code_from_hit(item) -> str:
    if isinstance(item, tuple):
        return item[0].section.section_code
    return item.section_code


def rank_for_sections(hits, wanted: set[str]) -> int | None:
    for rank, item in enumerate(hits, start=1):
        if section_code_from_hit(item) in wanted:
            return rank
    return None


def rank_for_section(hits, section_code: str) -> int | None:
    for rank, item in enumerate(hits, start=1):
        if section_code_from_hit(item) == section_code:
            return rank
    return None


def best_expected_fused(fused, wanted: set[str]):
    for rank, result in enumerate(fused, start=1):
        if result.section_code in wanted:
            return rank, result
    return None, None


def fmt_rank(value: int | None) -> str:
    return str(value) if value is not None else "not in top 20"


def duplicate_summary(results, limit: int = 5) -> str:
    counts = Counter(result.section_code for result in results[:limit])
    dupes = [
        f"{section} x{count}"
        for section, count in counts.items()
        if count > 1
    ]
    return ", ".join(dupes) if dupes else "none"


def print_leg(title: str, hits, wanted: set[str]) -> None:
    print()
    print(f"    {title}")
    print("    " + "-" * 66)

    for rank, (chunk, raw_score) in enumerate(hits, start=1):
        marker = "*" if chunk.section.section_code in wanted else " "
        print(
            f"    {marker}{rank:>2}. "
            f"{chunk.section.section_code:<10} "
            f"chunk={chunk.chunk_index + 1}/{chunk.chunk_total:<2} "
            f"raw={raw_score:.6f}"
        )


async def main(verbose: bool) -> None:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    cases = [
        case
        for case in payload["questions"]
        if case["expected_sections"]
    ]

    factory = get_session_factory()
    embedder = OpenAIEmbedder()

    hits_at_1 = 0
    hits_at_5 = 0
    diagnostics: list[dict] = []

    try:
        async with factory() as session:
            for case in cases:
                original_query = case["question"].strip()
                expansion = expand_acronyms(original_query)
                query = expansion.expanded
                query_vector = await embedder.embed_query(query)

                vector_hits = await _vector_candidates(
                    session,
                    query_vector,
                    CANDIDATES_PER_LEG,
                )
                text_hits = await _text_candidates(
                    session,
                    query,
                    CANDIDATES_PER_LEG,
                )

                # Same candidate lists and RRF scoring as production.
                # A larger output limit exposes the full fused union for
                # diagnosis without changing production retrieval.
                fused = _fuse(
                    vector_hits,
                    text_hits,
                    CANDIDATES_PER_LEG * 2,
                )
                top5 = fused[:5]
                wanted = set(case["expected_sections"])

                rank1_ok = bool(
                    top5 and top5[0].section_code in wanted
                )
                rank5_ok = bool(
                    wanted & {result.section_code for result in top5}
                )

                hits_at_1 += int(rank1_ok)
                hits_at_5 += int(rank5_ok)

                if rank1_ok:
                    continue

                expected_vector_rank = rank_for_sections(
                    vector_hits,
                    wanted,
                )
                expected_text_rank = rank_for_sections(
                    text_hits,
                    wanted,
                )
                expected_fused_rank, expected_result = best_expected_fused(
                    fused,
                    wanted,
                )

                winner = top5[0]
                winner_vector_rank = rank_for_section(
                    vector_hits,
                    winner.section_code,
                )
                winner_text_rank = rank_for_section(
                    text_hits,
                    winner.section_code,
                )

                diagnostics.append(
                    {
                        "case": case,
                        "expansion": expansion,
                        "vector_hits": vector_hits,
                        "text_hits": text_hits,
                        "fused": fused,
                        "top5": top5,
                        "expected_vector_rank": expected_vector_rank,
                        "expected_text_rank": expected_text_rank,
                        "expected_fused_rank": expected_fused_rank,
                        "expected_result": expected_result,
                        "winner": winner,
                        "winner_vector_rank": winner_vector_rank,
                        "winner_text_rank": winner_text_rank,
                    }
                )

        total = len(cases)

        print("Waypoint production ranking diagnostic")
        print("=" * 39)
        print(f"Questions:                 {QUESTIONS_PATH}")
        print(f"Embedding model:           {embedder.model_name}")
        print(f"Candidates per leg:        {CANDIDATES_PER_LEG}")
        print(f"RRF K:                     {RRF_K}")
        print()
        print(f"Answerable questions:      {total}")
        print(
            f"Recall@1:                  "
            f"{hits_at_1}/{total} ({hits_at_1 / total:.0%})"
        )
        print(
            f"Recall@5:                  "
            f"{hits_at_5}/{total} ({hits_at_5 / total:.0%})"
        )
        print(f"Rank-1 misses:             {len(diagnostics)}")

        for number, item in enumerate(diagnostics, start=1):
            case = item["case"]
            wanted = set(case["expected_sections"])
            winner = item["winner"]
            expected_result = item["expected_result"]

            print()
            print("=" * 76)
            print(f"MISS {number}: {case['question']}")
            print(f"Wanted: {', '.join(case['expected_sections'])}")

            if item["expansion"].changed:
                print(f"Expanded: {item['expansion'].expanded}")

            print()
            print("Fused top 5")
            print("-" * 76)

            for rank, result in enumerate(item["top5"], start=1):
                marker = "*" if result.section_code in wanted else " "
                print(
                    f"{marker}{rank}. {result.section_code:<10} "
                    f"chunk={result.chunk_index + 1}/{result.chunk_total:<2} "
                    f"rrf={result.score:.6f} "
                    f"vector={result.vector_rank or '-':>2} "
                    f"text={result.text_rank or '-':>2} "
                    f"both={'yes' if result.matched_both else 'no'}"
                )

            print()
            print("Expected-section ranks")
            print("-" * 76)
            print(
                f"Vector leg:                "
                f"{fmt_rank(item['expected_vector_rank'])}"
            )
            print(
                f"FTS leg:                   "
                f"{fmt_rank(item['expected_text_rank'])}"
            )
            print(
                f"Fused:                     "
                f"{item['expected_fused_rank'] or 'not in candidate union'}"
            )

            print()
            print("Rank-1 winner")
            print("-" * 76)
            print(f"Section:                   {winner.section_code}")
            print(
                f"Vector leg:                "
                f"{fmt_rank(item['winner_vector_rank'])}"
            )
            print(
                f"FTS leg:                   "
                f"{fmt_rank(item['winner_text_rank'])}"
            )
            print(
                f"Matched both legs:         "
                f"{'yes' if winner.matched_both else 'no'}"
            )

            if expected_result is not None:
                gap = winner.score - expected_result.score
                print(f"RRF score gap to expected: {gap:.6f}")
                print(
                    f"Expected matched both:     "
                    f"{'yes' if expected_result.matched_both else 'no'}"
                )

            print(
                f"Duplicate sections top 5:  "
                f"{duplicate_summary(item['top5'])}"
            )

            signals: list[str] = []

            if (
                expected_result is not None
                and winner.matched_both
                and not expected_result.matched_both
            ):
                signals.append(
                    "winner gets cross-leg agreement while the expected "
                    "chunk appears in only one retrieval leg"
                )

            if (
                item["expected_vector_rank"] is not None
                and item["winner_vector_rank"] is not None
                and item["winner_vector_rank"]
                < item["expected_vector_rank"]
            ):
                signals.append(
                    "vector leg favours the rank-1 winner over the expected "
                    "section"
                )

            if (
                item["expected_text_rank"] is not None
                and item["winner_text_rank"] is not None
                and item["winner_text_rank"]
                < item["expected_text_rank"]
            ):
                signals.append(
                    "FTS leg favours the rank-1 winner over the expected "
                    "section"
                )

            counts = Counter(
                result.section_code for result in item["top5"]
            )
            if any(count > 1 for count in counts.values()):
                signals.append(
                    "multiple chunks from one or more sections occupy the "
                    "fused top 5"
                )

            if not signals:
                signals.append(
                    "no single dominant heuristic signal; inspect the leg "
                    "rankings and RRF score gap"
                )

            print()
            print("Diagnostic signals")
            print("-" * 76)
            for signal in signals:
                print(f"- {signal}")

            if verbose:
                print_leg(
                    "Vector top 20",
                    item["vector_hits"],
                    wanted,
                )
                print_leg(
                    "FTS top 20",
                    item["text_hits"],
                    wanted,
                )

        print()
        print("=" * 76)
        print(
            "Read-only diagnostic complete. "
            "No corpus or database rows were changed."
        )

    finally:
        await dispose_engine()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Diagnose production hybrid-ranking rank-1 misses."
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full top-20 vector and FTS candidates for each miss.",
    )
    args = parser.parse_args()
    asyncio.run(main(args.verbose))