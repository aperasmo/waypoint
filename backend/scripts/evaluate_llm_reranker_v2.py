"""Read-only A/B test: production top-5 vs LLM-selected best passage."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from openai import AsyncOpenAI
from pydantic import BaseModel, Field, ValidationError

from app.config import get_settings
from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder
from app.retrieval.retriever import retrieve

QUESTIONS_PATH = Path(__file__).parent.parent / "tests" / "eval_questions_adjudicated_v2.json"

SYSTEM_PROMPT = """You are a retrieval reranker for the New Zealand Immigration
Operational Manual. You will receive one user question and exactly five passages
already retrieved from the manual.

Choose the passage that most directly contains the published rule needed to
answer the question.

Rules:
- Do not answer the immigration question.
- Do not use outside knowledge.
- Judge only from the supplied passages.
- Prefer the specific operative rule over a broad overview, adjacent rule,
  definition, or merely related topic.
- If multiple passages come from the same section, choose the passage whose
  text most directly addresses the question.
- Return JSON only: {"best_index": 1}
- best_index must be an integer from 1 to 5.
"""


class Choice(BaseModel):
    best_index: int = Field(ge=1, le=5)


def format_candidates(results) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        blocks.append(
            f"Candidate {i}\n"
            f"Section: {r.section_code}\n"
            f"Title: {r.title}\n"
            f"Chunk: {r.chunk_index + 1}/{r.chunk_total}\n"
            f"Passage:\n{r.text}"
        )
    return "\n\n---\n\n".join(blocks)


async def choose_best(client, settings, question: str, results) -> int:
    completion = await client.chat.completions.create(
        model=settings.answer_model,
        max_completion_tokens=settings.answer_max_tokens,
        reasoning_effort=settings.answer_reasoning_effort,
        response_format={"type": "json_object"},
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Question: {question}\n\n"
                    f"Retrieved passages:\n\n{format_candidates(results)}"
                ),
            },
        ],
    )

    raw = completion.choices[0].message.content or "{}"
    try:
        return Choice.model_validate(json.loads(raw)).best_index
    except (json.JSONDecodeError, ValidationError) as exc:
        raise RuntimeError(
            f"Malformed reranker output for {question!r}: {raw!r}"
        ) from exc


async def main() -> None:
    settings = get_settings()
    cases = [
        c
        for c in json.loads(
            QUESTIONS_PATH.read_text(encoding="utf-8")
        )["questions"]
        if c["expected_sections"]
    ]

    factory = get_session_factory()
    embedder = OpenAIEmbedder()
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    production_hits = 0
    reranked_hits = 0
    gains = []
    regressions = []
    misses = []

    try:
        async with factory() as session:
            print("Waypoint top-5 LLM reranker A/B - adjudicated v2")
            print("=" * 32)
            print(f"Questions:                 {QUESTIONS_PATH}")
            print(f"Retriever top-k:           5")
            print(f"Reranker model:            {settings.answer_model}")
            print(f"Reasoning effort:          {settings.answer_reasoning_effort}")
            print(f"Max completion tokens:     {settings.answer_max_tokens}")
            print()
            print("Running retrieval + reranking...")

            for n, case in enumerate(cases, start=1):
                question = case["question"]
                expected = set(case["expected_sections"])

                results = await retrieve(session, question, embedder, limit=5)
                if len(results) != 5:
                    raise RuntimeError(
                        f"Expected 5 results for {question!r}; got {len(results)}"
                    )

                sections = [r.section_code for r in results]
                if not expected & set(sections):
                    raise RuntimeError(
                        f"Top-5 coverage regression for {question!r}: "
                        f"wanted {case['expected_sections']}, got {sections}"
                    )

                production_ok = results[0].section_code in expected
                production_hits += int(production_ok)

                best_index = await choose_best(
                    client, settings, question, results
                )
                chosen = results[best_index - 1]
                reranked_ok = chosen.section_code in expected
                reranked_hits += int(reranked_ok)

                record = (
                    question,
                    case["expected_sections"],
                    sections,
                    chosen.section_code,
                )
                if not production_ok and reranked_ok:
                    gains.append(record)
                elif production_ok and not reranked_ok:
                    regressions.append(record)
                elif not production_ok and not reranked_ok:
                    misses.append(record)

                print(
                    f"[{n:>2}/{len(cases)}] "
                    f"{'OK' if reranked_ok else 'MISS':<4} "
                    f"production={results[0].section_code:<8} "
                    f"reranked={chosen.section_code:<8}"
                )

        total = len(cases)
        print()
        print("Results")
        print("-" * 76)
        print(
            f"Production Recall@1:       {production_hits}/{total} "
            f"({production_hits / total:.0%})"
        )
        print(
            f"Reranked Recall@1:         {reranked_hits}/{total} "
            f"({reranked_hits / total:.0%})"
        )
        print(f"Recall@1 delta:            {reranked_hits - production_hits:+d}")
        print(f"Top-5 candidate coverage:  {total}/{total} (100%)")
        print(f"Rank-1 gains:              {len(gains)}")
        print(f"Rank-1 regressions:        {len(regressions)}")
        print(f"Still-missed rank-1 cases: {len(misses)}")

        def show(title, rows):
            print()
            if not rows:
                print(f"{title}: none")
                return
            print(f"{title} ({len(rows)})")
            print("-" * 76)
            for question, expected, sections, chosen in rows:
                print(question)
                print(f"    wanted:   {', '.join(expected)}")
                print(f"    top 5:    {', '.join(sections)}")
                print(f"    reranker: {chosen}")

        show("Rank-1 gains", gains)
        show("Rank-1 regressions", regressions)
        show("Unchanged rank-1 misses", misses)

        print()
        print("Decision")
        print("-" * 76)
        if reranked_hits < production_hits:
            verdict = "REJECT"
            reason = "Reranker reduced Recall@1."
        elif regressions:
            verdict = "REVIEW"
            reason = (
                "Net Recall@1 did not regress, but previously correct "
                "rank-1 cases were displaced."
            )
        elif reranked_hits > production_hits:
            verdict = "MEASURED GAIN"
            reason = (
                "Recall@1 improved with no rank-1 regressions and the same "
                "top-5 evidence set."
            )
        else:
            verdict = "NO MEASURED GAIN"
            reason = "Recall@1 was unchanged."

        print(f"Verdict: {verdict}")
        print(f"Reason:  {reason}")
        print()
        print(
            "Read-only A/B complete. No corpus, retriever, database, "
            "chunking, or embedding changes were made."
        )

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())