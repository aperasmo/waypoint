"""Prepare the untouched external holdout-v2 adjudication packet.

Purpose
-------
Create a review artifact for the 60 fresh external holdout-v2 questions without
assigning gold labels and without calling the answer model or reranker.

The packet contains:
- the raw question metadata;
- production hybrid top-10 retrieval candidates for each question as REVIEW AIDS;
- one complete snapshot of all substantive corpus sections/chunks;
- a deterministic SHA256 fingerprint of that corpus snapshot.

Important
---------
Retrieval candidates do NOT define gold. The complete corpus snapshot must be
reviewed before assigning corpus_gap.

This script also enforces the pre-holdout candidate freeze. It refuses to run if:
- app/api/routes/ask.py no longer matches the frozen candidate SHA;
- tests/answer_candidate_v2_freeze.json no longer matches the freeze SHA;
- the raw holdout-v2 file no longer matches the collected SHA.

It makes:
- embedding calls only for production retrieval candidates;
- NO answer-model calls;
- NO reranker calls;
- NO gold/adjudication assignments;
- NO database writes.

Run from backend/:
    uv run python -m py_compile scripts/prepare_external_holdout_v2_adjudication_packet.py
    uv run python -m scripts.prepare_external_holdout_v2_adjudication_packet

Input:
    tests/external_social_holdout_v2_raw.json

Output:
    tests/external_adjudication_packet_v2.json
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

INPUT_PATH = (
    BACKEND_DIR / "tests" / "external_social_holdout_v2_raw.json"
)
OUTPUT_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_packet_v2.json"
)
ASK_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
FREEZE_PATH = (
    BACKEND_DIR / "tests" / "answer_candidate_v2_freeze.json"
)

EXPECTED_INPUT_SCHEMA = "waypoint-external-social-holdout-v2-raw"
EXPECTED_INPUT_SHA256 = (
    "8EE5BDF10BFA2E4D940A07D97739F777"
    "310D58ADE316D775FF89E75CC164D893"
)
EXPECTED_ASK_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)
EXPECTED_FREEZE_SHA256 = (
    "0600D79FFC375C7CC8FC358722EE51A9"
    "8B0D979188F61FF8B4CBD7412A1CB03C"
)

RETRIEVER_TOP_K = 10

FORBIDDEN_GOLD_FIELDS = {
    "expected_sections",
    "expected_section",
    "partial_support_sections",
    "evidence_status",
    "benchmark_status",
    "adjudication_note",
    "decision_boundary",
    "outcome",
    "gold",
    "gold_status",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_file(path: Path) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")


def require_sha(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(
            f"SHA mismatch for {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to prepare holdout-v2 against a changed artifact."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")
    return payload


def validate_raw_questions(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise RuntimeError("Raw holdout-v2 file root must be an object.")

    if payload.get("schema") != EXPECTED_INPUT_SCHEMA:
        raise RuntimeError(
            f"Unexpected raw-question schema: {payload.get('schema')!r}"
        )

    if payload.get("candidate_freeze_sha256") != EXPECTED_FREEZE_SHA256:
        raise RuntimeError(
            "Raw holdout-v2 file is not linked to the expected candidate freeze."
        )

    if payload.get("runtime_ask_sha256_at_freeze") != EXPECTED_ASK_SHA256:
        raise RuntimeError(
            "Raw holdout-v2 file is not linked to the expected ask.py SHA."
        )

    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("Raw holdout-v2 file has no questions list.")

    declared_count = payload.get("candidate_count")
    if declared_count != len(questions):
        raise RuntimeError(
            f"candidate_count={declared_count!r} but found "
            f"{len(questions)} questions."
        )

    if len(questions) != 60:
        raise RuntimeError(
            f"Expected exactly 60 fresh holdout-v2 questions, got {len(questions)}."
        )

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    validated: list[dict] = []

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Question {index} is not an object.")

        leaked = FORBIDDEN_GOLD_FIELDS & set(item)
        if leaked:
            raise RuntimeError(
                f"Question {index} already contains gold/adjudication fields: "
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


def corpus_snapshot_sha256(corpus: list[dict]) -> str:
    canonical = json.dumps(
        corpus,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest().upper()


async def main() -> None:
    for path in (INPUT_PATH, ASK_PATH, FREEZE_PATH):
        require_file(path)

    require_sha(INPUT_PATH, EXPECTED_INPUT_SHA256)
    require_sha(ASK_PATH, EXPECTED_ASK_SHA256)
    require_sha(FREEZE_PATH, EXPECTED_FREEZE_SHA256)

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Output already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite an existing holdout-v2 packet."
        )

    freeze = load_json(FREEZE_PATH)
    if freeze.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError(
            "Candidate freeze does not identify the expected ask.py SHA."
        )
    if freeze.get("status") != "FROZEN_CANDIDATE_BEFORE_EXTERNAL_HOLDOUT_V2":
        raise RuntimeError(
            f"Unexpected candidate freeze status: {freeze.get('status')!r}"
        )

    raw_payload = load_json(INPUT_PATH)
    questions = validate_raw_questions(raw_payload)

    factory = get_session_factory()
    embedder = OpenAIEmbedder()

    packet_questions: list[dict] = []

    print("Waypoint external holdout-v2 adjudication packet")
    print("=" * 48)
    print(f"Input:                     {INPUT_PATH}")
    print(f"Candidate freeze:          {FREEZE_PATH}")
    print(f"Questions:                 {len(questions)}")
    print(f"Review candidate top-k:    {RETRIEVER_TOP_K}")
    print()
    print("ask.py freeze verified:    YES")
    print("Gold labels loaded:        NO")
    print("Answer-model calls:        NONE")
    print("Reranker calls:            NONE")
    print("Embedding calls:           retrieval candidates only")
    print("Database writes:           NONE")
    print()
    print("Preparing review candidates + complete corpus snapshot...")

    try:
        async with factory() as session:
            corpus = await load_full_corpus(session)
            corpus_sha = corpus_snapshot_sha256(corpus)

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
                        "source_title": item.get("source_title"),
                        "source_date": item.get("source_date"),
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
            "schema": "waypoint-external-adjudication-packet-v2",
            "status": "UNADJUDICATED_FRESH_HOLDOUT_REVIEW_PACKET",
            "raw_questions_sha256": sha256(INPUT_PATH),
            "candidate_freeze_sha256": sha256(FREEZE_PATH),
            "runtime_ask_sha256": sha256(ASK_PATH),
            "question_count": len(packet_questions),
            "retriever_top_k": RETRIEVER_TOP_K,
            "corpus_section_count": len(corpus),
            "corpus_snapshot_sha256": corpus_sha,
            "rules": [
                (
                    "this is fresh external holdout-v2 collected after the "
                    "answer candidate was frozen"
                ),
                (
                    "retrieval candidates are review/navigation aids only and "
                    "must not define the gold answer"
                ),
                (
                    "review the complete corpus snapshot before assigning "
                    "corpus_gap"
                ),
                (
                    "social-media replies are not authoritative and are not "
                    "included in this packet"
                ),
                (
                    "expected_sections, evidence_status, benchmark_status, and "
                    "other gold labels must be assigned only during independent "
                    "human adjudication"
                ),
                (
                    "do not run the answer candidate on this holdout before "
                    "adjudication is reviewed and frozen"
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

        lowered = serialised.lower()
        leaked = [
            field
            for field in FORBIDDEN_GOLD_FIELDS
            if f'"{field.lower()}"' in lowered
        ]
        if leaked:
            raise RuntimeError(
                "Adjudication packet unexpectedly contains gold fields: "
                + ", ".join(sorted(leaked))
            )

        OUTPUT_PATH.write_text(serialised, encoding="utf-8")

        verify = load_json(OUTPUT_PATH)

        if verify.get("question_count") != len(questions):
            raise RuntimeError("Question count changed in output packet.")
        if verify.get("corpus_section_count") != len(corpus):
            raise RuntimeError("Corpus section count changed in output packet.")
        if verify.get("corpus_snapshot_sha256") != corpus_sha:
            raise RuntimeError("Corpus snapshot SHA verification failed.")
        if verify.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
            raise RuntimeError("Frozen ask.py SHA was not preserved in packet.")
        if verify.get("candidate_freeze_sha256") != EXPECTED_FREEZE_SHA256:
            raise RuntimeError("Candidate freeze SHA was not preserved in packet.")

        print()
        print(f"Output:                    {OUTPUT_PATH}")
        print(f"Raw holdout SHA256:        {sha256(INPUT_PATH)}")
        print(f"Candidate freeze SHA256:   {sha256(FREEZE_PATH)}")
        print(f"ask.py SHA256:             {sha256(ASK_PATH)}")
        print(f"Corpus snapshot SHA256:    {corpus_sha}")
        print(f"Packet SHA256:             {sha256(OUTPUT_PATH)}")
        print(f"Questions preserved:       {len(packet_questions)}")
        print(f"Corpus sections exported:  {len(corpus)}")
        print()
        print("Gold/adjudication fields:  NONE")
        print("Answer-model calls:        NONE")
        print("Reranker calls:            NONE")
        print("Database writes:           NONE")
        print("External holdout-v2 adjudication packet: PASS")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
