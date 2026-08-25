"""Prepare a blind evidence packet for external-question adjudication.

Purpose
-------
Create a review artifact for the 60 raw social-media questions without assigning
gold labels or using an LLM.

The packet contains:
- the raw question metadata;
- production hybrid top-10 candidate references for each question;
- a complete snapshot of all substantive corpus sections/chunks once.

Why include the full corpus?
----------------------------
Gold adjudication must not depend solely on the retriever being evaluated. If a
relevant section is not in a question's top 10, the reviewer can still search
the complete corpus snapshot before deciding "corpus_gap".

This script:
- calls the existing production retriever only to provide review candidates;
- reads all substantive corpus text directly from PostgreSQL;
- makes no LLM calls;
- assigns no expected_sections;
- assigns no evidence_status;
- performs no database writes.

Run from backend/:
    uv run python -m scripts.prepare_external_adjudication_packet

Expected input:
    tests/external_social_questions_raw_v2.json

Expected output:
    tests/external_adjudication_packet_v1.json
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder
from app.models.schema import Chunk, Section
from app.retrieval.retriever import retrieve


BACKEND_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BACKEND_DIR / "tests" / "external_social_questions_raw_v2.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "external_adjudication_packet_v1.json"

EXPECTED_INPUT_SCHEMA = "waypoint-external-social-questions-raw-v2"
RETRIEVER_TOP_K = 10


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_raw_questions(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise RuntimeError("Raw external question file root must be an object.")

    if payload.get("schema") != EXPECTED_INPUT_SCHEMA:
        raise RuntimeError(
            f"Unexpected raw-question schema: {payload.get('schema')!r}"
        )

    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("Raw external question file has no questions list.")

    declared_count = payload.get("candidate_count")
    if declared_count != len(questions):
        raise RuntimeError(
            f"candidate_count={declared_count!r} but found "
            f"{len(questions)} questions."
        )

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    validated: list[dict] = []

    forbidden = {
        "expected_sections",
        "expected_section",
        "evidence_status",
        "decision_boundary",
        "outcome",
    }

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Question {index} is not an object.")

        leaked = forbidden & set(item)
        if leaked:
            raise RuntimeError(
                f"Question {index} already contains adjudication fields: "
                f"{sorted(leaked)}"
            )

        candidate_id = item.get("candidate_id")
        question = item.get("question")

        if not isinstance(candidate_id, str) or not candidate_id:
            raise RuntimeError(f"Question {index} has invalid candidate_id.")
        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(f"Question {index} has invalid question.")

        if candidate_id in seen_ids:
            raise RuntimeError(f"Duplicate candidate_id: {candidate_id}")
        if question.strip() in seen_questions:
            raise RuntimeError(f"Duplicate question: {question.strip()!r}")

        seen_ids.add(candidate_id)
        seen_questions.add(question.strip())
        validated.append(dict(item))

    return validated


async def load_full_corpus(session) -> list[dict]:
    stmt = (
        select(
            Section.section_code,
            Section.title,
            Section.source_url,
            Section.effective_date,
            Chunk.chunk_index,
            Chunk.chunk_total,
            Chunk.text,
        )
        .join(Chunk, Chunk.section_id == Section.id)
        .order_by(Section.section_code, Chunk.chunk_index)
    )

    result = await session.execute(stmt)

    metadata_by_code: dict[str, dict] = {}
    chunks_by_code: dict[str, list[dict]] = defaultdict(list)

    for (
        section_code,
        title,
        source_url,
        effective_date,
        chunk_index,
        chunk_total,
        text,
    ) in result.all():
        if not isinstance(section_code, str) or not section_code.strip():
            raise RuntimeError("Invalid section_code returned from database.")
        if not isinstance(text, str) or not text.strip():
            raise RuntimeError(f"{section_code}: empty chunk text.")

        code = section_code.strip()

        metadata = {
            "section_code": code,
            "title": title.strip() if isinstance(title, str) else "",
            "source_url": source_url,
            "effective_date": (
                effective_date.isoformat()
                if effective_date is not None
                else None
            ),
        }

        existing = metadata_by_code.get(code)
        if existing is None:
            metadata_by_code[code] = metadata
        elif existing != metadata:
            raise RuntimeError(
                f"Inconsistent section metadata for {code}."
            )

        chunks_by_code[code].append(
            {
                "chunk_index": int(chunk_index),
                "chunk_total": int(chunk_total),
                "text": text,
            }
        )

    corpus: list[dict] = []

    for code in sorted(metadata_by_code):
        chunks = sorted(
            chunks_by_code[code],
            key=lambda item: item["chunk_index"],
        )

        totals = {item["chunk_total"] for item in chunks}
        if len(totals) != 1:
            raise RuntimeError(
                f"{code}: inconsistent chunk_total values."
            )

        declared_total = next(iter(totals))
        if declared_total != len(chunks):
            raise RuntimeError(
                f"{code}: declared {declared_total} chunks, found "
                f"{len(chunks)}."
            )

        expected_indices = list(range(len(chunks)))
        actual_indices = [item["chunk_index"] for item in chunks]
        if actual_indices != expected_indices:
            raise RuntimeError(
                f"{code}: non-contiguous chunk indices {actual_indices}."
            )

        corpus.append(
            {
                **metadata_by_code[code],
                "chunks": chunks,
            }
        )

    if not corpus:
        raise RuntimeError("No substantive corpus sections were loaded.")

    return corpus


async def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Raw external question file not found: {INPUT_PATH}")

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Output already exists: {OUTPUT_PATH}\n"
            "Delete it deliberately before regenerating the adjudication packet."
        )

    raw_payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    questions = validate_raw_questions(raw_payload)

    factory = get_session_factory()
    embedder = OpenAIEmbedder()

    packet_questions: list[dict] = []

    print("Waypoint external adjudication packet")
    print("=" * 37)
    print(f"Input:                     {INPUT_PATH}")
    print(f"Questions:                 {len(questions)}")
    print(f"Review candidate top-k:    {RETRIEVER_TOP_K}")
    print()
    print("Gold labels loaded:        NO")
    print("LLM calls:                 NONE")
    print("Preparing review candidates + full corpus snapshot...")

    try:
        async with factory() as session:
            corpus = await load_full_corpus(session)

            for number, item in enumerate(questions, start=1):
                results = await retrieve(
                    session,
                    item["question"],
                    embedder,
                    limit=RETRIEVER_TOP_K,
                )

                if len(results) != RETRIEVER_TOP_K:
                    raise RuntimeError(
                        f"{item['candidate_id']}: expected "
                        f"{RETRIEVER_TOP_K} retrieval results, "
                        f"got {len(results)}."
                    )

                candidates = []
                for rank, result in enumerate(results, start=1):
                    candidates.append(
                        {
                            "rank": rank,
                            "section_code": result.section_code,
                            "title": result.title,
                            "chunk_index": result.chunk_index,
                            "chunk_total": result.chunk_total,
                            "rrf_score": result.score,
                            "vector_rank": result.vector_rank,
                            "text_rank": result.text_rank,
                            "matched_both": result.matched_both,
                        }
                    )

                packet_questions.append(
                    {
                        "candidate_id": item["candidate_id"],
                        "platform": item.get("platform"),
                        "community": item.get("community"),
                        "category": item.get("category"),
                        "question": item["question"].strip(),
                        "source_url": item.get("source_url"),
                        "source_access": item.get("source_access"),
                        "retrieval_candidates": candidates,
                    }
                )

                top_sections = ", ".join(
                    candidate["section_code"]
                    for candidate in candidates[:5]
                )

                print(
                    f"[{number:>2}/{len(questions)}] "
                    f"{item['candidate_id']} "
                    f"top5={top_sections}"
                )

        output = {
            "schema": "waypoint-external-adjudication-packet-v1",
            "status": "UNADJUDICATED_REVIEW_PACKET",
            "raw_questions_sha256": sha256(INPUT_PATH),
            "question_count": len(packet_questions),
            "retriever_top_k": RETRIEVER_TOP_K,
            "corpus_section_count": len(corpus),
            "rules": [
                (
                    "retrieval candidates are review aids only and must not "
                    "define the gold answer"
                ),
                (
                    "review the complete corpus snapshot before assigning "
                    "corpus_gap"
                ),
                (
                    "social-media answers are not authoritative and are not "
                    "included in this packet"
                ),
                (
                    "expected_sections and evidence_status must be assigned "
                    "only during the later adjudication step"
                ),
            ],
            "questions": packet_questions,
            "corpus_sections": corpus,
        }

        serialised = json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ) + "\n"

        forbidden_output_tokens = (
            '"expected_sections"',
            '"expected_section"',
            '"evidence_status"',
            '"decision_boundary"',
            '"outcome"',
        )

        lowered = serialised.lower()
        leaked = [
            token
            for token in forbidden_output_tokens
            if token.lower() in lowered
        ]
        if leaked:
            raise RuntimeError(
                "Adjudication packet unexpectedly contains gold fields: "
                + ", ".join(leaked)
            )

        OUTPUT_PATH.write_text(serialised, encoding="utf-8")

        verify = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

        if verify.get("question_count") != len(questions):
            raise RuntimeError("Question count changed in output packet.")
        if verify.get("corpus_section_count") != len(corpus):
            raise RuntimeError("Corpus section count changed in output packet.")

        print()
        print(f"Output:                    {OUTPUT_PATH}")
        print(f"Raw questions SHA256:      {sha256(INPUT_PATH)}")
        print(f"Packet SHA256:             {sha256(OUTPUT_PATH)}")
        print(f"Questions preserved:       {len(packet_questions)}")
        print(f"Corpus sections exported:  {len(corpus)}")
        print("Gold/adjudication fields:  none")
        print("Database writes:           NONE")
        print("External adjudication packet: PASS")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())