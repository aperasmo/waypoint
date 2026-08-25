"""Validate and freeze the external Waypoint adjudication set.

This is an evaluation-data utility, not runtime/ranking code.

It deliberately contains:
- no benchmark question literals;
- no candidate IDs;
- no INZ section-code mappings;
- no expected-answer mappings;
- no retrieval, embedding, reranker, or answer-model calls.

It validates the human-reviewed adjudication draft against the original
adjudication packet, then writes an immutable frozen gold artifact.

Run from backend/:
    uv run python -m py_compile scripts\freeze_external_adjudication.py
    uv run python -m scripts.freeze_external_adjudication

Inputs:
    tests/external_adjudication_packet_v1.json
    tests/external_adjudication_draft_v1.json

Output:
    tests/external_adjudication_gold_v1.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
PACKET_PATH = BACKEND_DIR / "tests" / "external_adjudication_packet_v1.json"
DRAFT_PATH = BACKEND_DIR / "tests" / "external_adjudication_draft_v1.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "external_adjudication_gold_v1.json"

EXPECTED_PACKET_SCHEMA = "waypoint-external-adjudication-packet-v1"
EXPECTED_DRAFT_SCHEMA = "waypoint-external-adjudication-draft-v1"

ALLOWED_EVIDENCE_STATUSES = {
    "sufficient",
    "corpus_gap",
    "external_source_required",
    None,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")

    return payload


def validate_packet(packet: dict) -> tuple[dict[str, dict], set[str]]:
    if packet.get("schema") != EXPECTED_PACKET_SCHEMA:
        raise RuntimeError(
            f"Unexpected packet schema: {packet.get('schema')!r}"
        )

    questions = packet.get("questions")
    corpus = packet.get("corpus_sections")

    if not isinstance(questions, list):
        raise RuntimeError("Packet questions must be a list.")
    if not isinstance(corpus, list):
        raise RuntimeError("Packet corpus_sections must be a list.")

    if packet.get("question_count") != len(questions):
        raise RuntimeError(
            "Packet question_count does not match questions list."
        )
    if packet.get("corpus_section_count") != len(corpus):
        raise RuntimeError(
            "Packet corpus_section_count does not match corpus list."
        )

    questions_by_id: dict[str, dict] = {}

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Packet question {index} is not an object.")

        candidate_id = item.get("candidate_id")
        question = item.get("question")

        if not isinstance(candidate_id, str) or not candidate_id:
            raise RuntimeError(
                f"Packet question {index} has invalid candidate_id."
            )
        if candidate_id in questions_by_id:
            raise RuntimeError(
                f"Duplicate packet candidate_id: {candidate_id}"
            )
        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(
                f"Packet question {index} has invalid question text."
            )

        questions_by_id[candidate_id] = item

    corpus_codes: set[str] = set()

    for index, section in enumerate(corpus, start=1):
        if not isinstance(section, dict):
            raise RuntimeError(f"Corpus section {index} is not an object.")

        code = section.get("section_code")
        if not isinstance(code, str) or not code:
            raise RuntimeError(
                f"Corpus section {index} has invalid section_code."
            )
        if code in corpus_codes:
            raise RuntimeError(f"Duplicate corpus section code: {code}")

        corpus_codes.add(code)

    return questions_by_id, corpus_codes


def validate_draft(
    draft: dict,
    packet: dict,
    packet_questions: dict[str, dict],
    corpus_codes: set[str],
) -> tuple[list[dict], Counter, Counter]:
    if draft.get("schema") != EXPECTED_DRAFT_SCHEMA:
        raise RuntimeError(
            f"Unexpected draft schema: {draft.get('schema')!r}"
        )

    if draft.get("packet_sha256") != sha256(PACKET_PATH):
        raise RuntimeError(
            "Draft packet_sha256 does not match the current packet file."
        )

    if draft.get("raw_questions_sha256") != packet.get(
        "raw_questions_sha256"
    ):
        raise RuntimeError(
            "Draft raw_questions_sha256 does not match packet metadata."
        )

    questions = draft.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("Draft questions must be a list.")

    if draft.get("question_count") != len(questions):
        raise RuntimeError(
            "Draft question_count does not match questions list."
        )

    draft_ids: set[str] = set()
    status_counts: Counter = Counter()
    benchmark_counts: Counter = Counter()

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Draft question {index} is not an object.")

        candidate_id = item.get("candidate_id")
        if not isinstance(candidate_id, str) or not candidate_id:
            raise RuntimeError(
                f"Draft question {index} has invalid candidate_id."
            )
        if candidate_id in draft_ids:
            raise RuntimeError(
                f"Duplicate draft candidate_id: {candidate_id}"
            )
        if candidate_id not in packet_questions:
            raise RuntimeError(
                f"Draft contains unknown candidate_id: {candidate_id}"
            )

        draft_ids.add(candidate_id)

        # The gold freeze must preserve the original blind question exactly.
        packet_question = packet_questions[candidate_id].get("question")
        if item.get("question") != packet_question:
            raise RuntimeError(
                f"{candidate_id}: question text differs from packet."
            )

        status = item.get("evidence_status")
        if status not in ALLOWED_EVIDENCE_STATUSES:
            raise RuntimeError(
                f"{candidate_id}: invalid evidence_status {status!r}."
            )

        expected_sections = item.get("expected_sections")
        partial_sections = item.get("partial_support_sections")
        benchmark_status = item.get("benchmark_status")
        note = item.get("adjudication_note")

        if not isinstance(expected_sections, list):
            raise RuntimeError(
                f"{candidate_id}: expected_sections must be a list."
            )
        if not isinstance(partial_sections, list):
            raise RuntimeError(
                f"{candidate_id}: partial_support_sections must be a list."
            )
        if not isinstance(benchmark_status, str) or not benchmark_status:
            raise RuntimeError(
                f"{candidate_id}: invalid benchmark_status."
            )
        if not isinstance(note, str) or not note.strip():
            raise RuntimeError(
                f"{candidate_id}: adjudication_note is required."
            )

        for field_name, codes in (
            ("expected_sections", expected_sections),
            ("partial_support_sections", partial_sections),
        ):
            if len(codes) != len(set(codes)):
                raise RuntimeError(
                    f"{candidate_id}: duplicate values in {field_name}."
                )

            for code in codes:
                if not isinstance(code, str) or not code:
                    raise RuntimeError(
                        f"{candidate_id}: invalid section in {field_name}."
                    )
                if code not in corpus_codes:
                    raise RuntimeError(
                        f"{candidate_id}: section {code} in {field_name} "
                        "does not exist in frozen packet corpus."
                    )

        # Core adjudication invariants.
        if status == "sufficient":
            if not expected_sections:
                raise RuntimeError(
                    f"{candidate_id}: sufficient case requires gold "
                    "expected_sections."
                )
            if partial_sections:
                raise RuntimeError(
                    f"{candidate_id}: sufficient case must not also use "
                    "partial_support_sections."
                )

        elif status in {
            "corpus_gap",
            "external_source_required",
        }:
            if expected_sections:
                raise RuntimeError(
                    f"{candidate_id}: non-sufficient case must not have "
                    "expected_sections."
                )

        elif status is None:
            if not benchmark_status.startswith("exclude_"):
                raise RuntimeError(
                    f"{candidate_id}: unlabelled case must be excluded."
                )
            if expected_sections:
                raise RuntimeError(
                    f"{candidate_id}: excluded unlabelled case must not "
                    "have expected_sections."
                )

        if benchmark_status == "include" and status is None:
            raise RuntimeError(
                f"{candidate_id}: included case cannot have null "
                "evidence_status."
            )

        status_counts[status or "unlabelled_excluded"] += 1
        benchmark_counts[benchmark_status] += 1

    if draft_ids != set(packet_questions):
        missing = sorted(set(packet_questions) - draft_ids)
        extra = sorted(draft_ids - set(packet_questions))
        raise RuntimeError(
            "Draft and packet candidate IDs differ. "
            f"missing={missing}, extra={extra}"
        )

    return questions, status_counts, benchmark_counts


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Frozen output already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite an existing gold artifact."
        )

    packet = load_json(PACKET_PATH)
    draft = load_json(DRAFT_PATH)

    packet_questions, corpus_codes = validate_packet(packet)
    questions, status_counts, benchmark_counts = validate_draft(
        draft,
        packet,
        packet_questions,
        corpus_codes,
    )

    rank_scorable = [
        item
        for item in questions
        if (
            item["benchmark_status"] == "include"
            and item["evidence_status"] == "sufficient"
        )
    ]

    evidence_scorable = [
        item
        for item in questions
        if (
            item["benchmark_status"] == "include"
            and item["evidence_status"] is not None
        )
    ]

    frozen = {
        "schema": "waypoint-external-adjudication-gold-v1",
        "status": "FROZEN_DO_NOT_TUNE_ON_THIS_SET",
        "freeze_date": date.today().isoformat(),
        "source_packet_sha256": sha256(PACKET_PATH),
        "source_draft_sha256": sha256(DRAFT_PATH),
        "raw_questions_sha256": packet["raw_questions_sha256"],
        "question_count": len(questions),
        "corpus_section_count": len(corpus_codes),
        "evidence_scorable_count": len(evidence_scorable),
        "rank_scorable_count": len(rank_scorable),
        "adjudication_rules": list(draft.get("adjudication_rules", [])),
        "freeze_rules": [
            (
                "This file is evaluation gold and must never be imported "
                "by runtime retrieval, ranking, reranking, or answer code."
            ),
            (
                "Do not change the reranker prompt, retrieval weights, "
                "section boosts, or answer classifier in response to "
                "individual failures on this frozen set."
            ),
            (
                "If this frozen set is used for tuning, it becomes a "
                "development set and a new untouched holdout is required."
            ),
        ],
        "evidence_status_counts": dict(status_counts),
        "benchmark_status_counts": dict(benchmark_counts),
        "questions": questions,
    }

    OUTPUT_PATH.write_text(
        json.dumps(frozen, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Re-read and revalidate immutable core fields after serialisation.
    verify = load_json(OUTPUT_PATH)

    if verify.get("source_packet_sha256") != sha256(PACKET_PATH):
        raise RuntimeError("Frozen packet SHA verification failed.")
    if verify.get("source_draft_sha256") != sha256(DRAFT_PATH):
        raise RuntimeError("Frozen draft SHA verification failed.")
    if verify.get("question_count") != len(questions):
        raise RuntimeError("Frozen question count verification failed.")
    if verify.get("rank_scorable_count") != len(rank_scorable):
        raise RuntimeError("Frozen rank-scorable count verification failed.")

    print("Waypoint external adjudication freeze")
    print("=" * 37)
    print(f"Packet:                    {PACKET_PATH}")
    print(f"Draft:                     {DRAFT_PATH}")
    print(f"Output:                    {OUTPUT_PATH}")
    print()
    print(f"Questions frozen:          {len(questions)}")
    print(f"Evidence-scorable:         {len(evidence_scorable)}")
    print(f"Rank-scorable sufficient:  {len(rank_scorable)}")
    print(
        "Evidence status counts:    "
        + json.dumps(dict(status_counts), sort_keys=True)
    )
    print(
        "Benchmark status counts:   "
        + json.dumps(dict(benchmark_counts), sort_keys=True)
    )
    print()
    print(f"Packet SHA256:             {sha256(PACKET_PATH)}")
    print(f"Draft SHA256:              {sha256(DRAFT_PATH)}")
    print(f"Frozen gold SHA256:        {sha256(OUTPUT_PATH)}")
    print()
    print("Question text preserved:   PASS")
    print("Section references valid:  PASS")
    print("Gold invariants:            PASS")
    print("Runtime/model calls:        NONE")
    print("Database writes:            NONE")
    print("External adjudication freeze: PASS")


if __name__ == "__main__":
    main()
