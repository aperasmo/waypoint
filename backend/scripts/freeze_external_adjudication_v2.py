"""Freeze the reviewed external holdout-v2 adjudication draft as gold.

This script performs validation and file transformation only.

It does NOT:
- call app.api.routes.ask;
- call retrieval, embeddings, reranking, or an answer model;
- modify runtime code;
- write to the database.

Run from backend/:
    uv run python -m py_compile scripts/freeze_external_adjudication_v2.py
    uv run python -m scripts.freeze_external_adjudication_v2

Inputs:
    tests/external_adjudication_draft_v2.json
    tests/external_adjudication_packet_v2.json
    tests/external_social_holdout_v2_raw.json
    tests/answer_candidate_v2_freeze.json
    app/api/routes/ask.py

Output:
    tests/external_adjudication_gold_v2.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

DRAFT_PATH = BACKEND_DIR / "tests" / "external_adjudication_draft_v2.json"
PACKET_PATH = BACKEND_DIR / "tests" / "external_adjudication_packet_v2.json"
RAW_PATH = BACKEND_DIR / "tests" / "external_social_holdout_v2_raw.json"
FREEZE_PATH = BACKEND_DIR / "tests" / "answer_candidate_v2_freeze.json"
ASK_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
OUTPUT_PATH = BACKEND_DIR / "tests" / "external_adjudication_gold_v2.json"

EXPECTED_DRAFT_SHA256 = (
    "2E9CD2AA09E8FA7EDAF586E239CCD896"
    "D305E80B91E583E6DCC4652FC9E24F45"
)
EXPECTED_PACKET_SHA256 = (
    "2D4F12A75ECAA30378CD6E601814653C"
    "3CD42F6C893E486D1F59362DB8646F2A"
)
EXPECTED_RAW_SHA256 = (
    "8EE5BDF10BFA2E4D940A07D97739F777"
    "310D58ADE316D775FF89E75CC164D893"
)
EXPECTED_CANDIDATE_FREEZE_SHA256 = (
    "0600D79FFC375C7CC8FC358722EE51A9"
    "8B0D979188F61FF8B4CBD7412A1CB03C"
)
EXPECTED_ASK_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)
EXPECTED_CORPUS_SNAPSHOT_SHA256 = (
    "DF8C74B67AABC12C68C301655F8962ED"
    "4038D3897EFAC0EE3A95DC901EF977FC"
)

EXPECTED_DRAFT_SCHEMA = "waypoint-external-adjudication-draft-v2"
EXPECTED_PACKET_SCHEMA = "waypoint-external-adjudication-packet-v2"
EXPECTED_RAW_SCHEMA = "waypoint-external-social-holdout-v2-raw"

EVIDENCE_STATUSES = {
    "sufficient",
    "corpus_gap",
    "external_source_required",
}

EXPECTED_COUNTS = {
    "sufficient": 16,
    "corpus_gap": 34,
    "external_source_required": 10,
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


def require_sha(path: Path, expected: str) -> None:
    actual = sha256(path)
    if actual != expected:
        raise SystemExit(
            f"SHA mismatch for {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze a changed artifact."
        )


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Frozen gold already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite an existing holdout-v2 gold artifact."
        )

    for path, expected in (
        (DRAFT_PATH, EXPECTED_DRAFT_SHA256),
        (PACKET_PATH, EXPECTED_PACKET_SHA256),
        (RAW_PATH, EXPECTED_RAW_SHA256),
        (FREEZE_PATH, EXPECTED_CANDIDATE_FREEZE_SHA256),
        (ASK_PATH, EXPECTED_ASK_SHA256),
    ):
        require_sha(path, expected)

    draft = load_json(DRAFT_PATH)
    packet = load_json(PACKET_PATH)
    raw = load_json(RAW_PATH)
    candidate_freeze = load_json(FREEZE_PATH)

    if draft.get("schema") != EXPECTED_DRAFT_SCHEMA:
        raise RuntimeError(f"Unexpected draft schema: {draft.get('schema')!r}")
    if draft.get("status") != "DRAFT_FOR_HUMAN_REVIEW_DO_NOT_SCORE":
        raise RuntimeError(f"Unexpected draft status: {draft.get('status')!r}")
    if packet.get("schema") != EXPECTED_PACKET_SCHEMA:
        raise RuntimeError(f"Unexpected packet schema: {packet.get('schema')!r}")
    if raw.get("schema") != EXPECTED_RAW_SCHEMA:
        raise RuntimeError(f"Unexpected raw schema: {raw.get('schema')!r}")

    if candidate_freeze.get("status") != "FROZEN_CANDIDATE_BEFORE_EXTERNAL_HOLDOUT_V2":
        raise RuntimeError("Candidate freeze has an unexpected status.")
    if candidate_freeze.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError("Candidate freeze does not identify the expected ask.py SHA.")

    if draft.get("packet_sha256") != EXPECTED_PACKET_SHA256:
        raise RuntimeError("Draft is not linked to the expected adjudication packet.")
    if draft.get("raw_questions_sha256") != EXPECTED_RAW_SHA256:
        raise RuntimeError("Draft is not linked to the expected raw holdout-v2 file.")
    if draft.get("candidate_freeze_sha256") != EXPECTED_CANDIDATE_FREEZE_SHA256:
        raise RuntimeError("Draft is not linked to the expected candidate freeze.")
    if draft.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError("Draft is not linked to the expected ask.py candidate.")
    if draft.get("corpus_snapshot_sha256") != EXPECTED_CORPUS_SNAPSHOT_SHA256:
        raise RuntimeError("Draft corpus snapshot SHA does not match the frozen snapshot.")

    if packet.get("raw_questions_sha256") != EXPECTED_RAW_SHA256:
        raise RuntimeError("Packet is not linked to the expected raw holdout-v2 file.")
    if packet.get("candidate_freeze_sha256") != EXPECTED_CANDIDATE_FREEZE_SHA256:
        raise RuntimeError("Packet is not linked to the expected candidate freeze.")
    if packet.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError("Packet is not linked to the expected ask.py candidate.")
    if packet.get("corpus_snapshot_sha256") != EXPECTED_CORPUS_SNAPSHOT_SHA256:
        raise RuntimeError("Packet corpus snapshot SHA changed.")

    if raw.get("candidate_freeze_sha256") != EXPECTED_CANDIDATE_FREEZE_SHA256:
        raise RuntimeError("Raw holdout is not linked to the expected candidate freeze.")
    if raw.get("runtime_ask_sha256_at_freeze") != EXPECTED_ASK_SHA256:
        raise RuntimeError("Raw holdout is not linked to the expected ask.py candidate.")

    draft_questions = draft.get("questions")
    packet_questions = packet.get("questions")
    raw_questions = raw.get("questions")
    corpus_sections = packet.get("corpus_sections")

    if not isinstance(draft_questions, list):
        raise RuntimeError("Draft questions must be a list.")
    if not isinstance(packet_questions, list):
        raise RuntimeError("Packet questions must be a list.")
    if not isinstance(raw_questions, list):
        raise RuntimeError("Raw questions must be a list.")
    if not isinstance(corpus_sections, list):
        raise RuntimeError("Packet corpus_sections must be a list.")

    if len(draft_questions) != 60:
        raise RuntimeError(f"Expected 60 draft questions, got {len(draft_questions)}.")
    if len(packet_questions) != 60 or len(raw_questions) != 60:
        raise RuntimeError("Packet/raw question count is no longer 60.")

    corpus_codes = {
        section.get("section_code")
        for section in corpus_sections
        if isinstance(section, dict)
    }
    if len(corpus_codes) != 125:
        raise RuntimeError(f"Expected 125 corpus section codes, got {len(corpus_codes)}.")

    raw_by_id = {item["candidate_id"]: item for item in raw_questions}
    packet_by_id = {item["candidate_id"]: item for item in packet_questions}

    if len(raw_by_id) != 60 or len(packet_by_id) != 60:
        raise RuntimeError("Duplicate candidate IDs detected in raw or packet.")
    if set(raw_by_id) != set(packet_by_id):
        raise RuntimeError("Raw and packet candidate sets differ.")

    frozen_questions: list[dict] = []
    seen_ids: set[str] = set()
    counts: Counter = Counter()
    source_urls: set[str] = set()

    for index, item in enumerate(draft_questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Draft question {index} is not an object.")

        case_id = item.get("candidate_id")
        question = item.get("question")
        status = item.get("evidence_status")
        benchmark_status = item.get("benchmark_status")
        expected_sections = item.get("expected_sections")
        partial_support_sections = item.get("partial_support_sections")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(f"Draft question {index} has invalid candidate_id.")
        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate candidate_id in draft: {case_id}")
        seen_ids.add(case_id)

        if case_id not in raw_by_id or case_id not in packet_by_id:
            raise RuntimeError(f"{case_id}: missing from raw or packet.")
        if question != raw_by_id[case_id].get("question"):
            raise RuntimeError(f"{case_id}: draft question differs from raw holdout.")
        if question != packet_by_id[case_id].get("question"):
            raise RuntimeError(f"{case_id}: draft question differs from packet.")
        if item.get("source_url") != raw_by_id[case_id].get("source_url"):
            raise RuntimeError(f"{case_id}: source URL differs from raw holdout.")

        if status not in EVIDENCE_STATUSES:
            raise RuntimeError(f"{case_id}: invalid evidence_status {status!r}.")
        if benchmark_status != "include":
            raise RuntimeError(f"{case_id}: all v2 draft cases must remain included.")
        if not isinstance(expected_sections, list):
            raise RuntimeError(f"{case_id}: expected_sections must be a list.")
        if not isinstance(partial_support_sections, list):
            raise RuntimeError(f"{case_id}: partial_support_sections must be a list.")

        for code in expected_sections + partial_support_sections:
            if code not in corpus_codes:
                raise RuntimeError(f"{case_id}: unknown corpus section code {code!r}.")

        if status == "sufficient":
            if not expected_sections:
                raise RuntimeError(f"{case_id}: sufficient case has no expected sections.")
            if partial_support_sections:
                raise RuntimeError(
                    f"{case_id}: sufficient case must not have partial_support_sections."
                )
        elif expected_sections:
            raise RuntimeError(
                f"{case_id}: non-sufficient case must not have expected_sections."
            )

        note = item.get("adjudication_note")
        if not isinstance(note, str) or not note.strip():
            raise RuntimeError(f"{case_id}: adjudication_note is missing.")

        counts[status] += 1
        source_urls.add(item.get("source_url"))
        frozen_questions.append(dict(item))

    if set(seen_ids) != set(raw_by_id):
        raise RuntimeError("Frozen draft candidate set does not match raw holdout.")
    if dict(counts) != EXPECTED_COUNTS:
        raise RuntimeError(
            f"Evidence-status counts changed.\n"
            f"Expected: {EXPECTED_COUNTS}\n"
            f"Actual:   {dict(counts)}"
        )
    if len(source_urls) != 20:
        raise RuntimeError(f"Expected 20 source clusters, got {len(source_urls)}.")

    gold = {
        "schema": "waypoint-external-adjudication-gold-v2",
        "status": "FROZEN_DO_NOT_TUNE_ON_THIS_SET",
        "draft_sha256": EXPECTED_DRAFT_SHA256,
        "packet_sha256": EXPECTED_PACKET_SHA256,
        "raw_questions_sha256": EXPECTED_RAW_SHA256,
        "candidate_freeze_sha256": EXPECTED_CANDIDATE_FREEZE_SHA256,
        "runtime_ask_sha256": EXPECTED_ASK_SHA256,
        "corpus_snapshot_sha256": EXPECTED_CORPUS_SNAPSHOT_SHA256,
        "question_count": 60,
        "included_question_count": 60,
        "unique_source_count": 20,
        "cluster_structure": "20 public source posts, 3 paraphrased questions per source",
        "evidence_status_counts": EXPECTED_COUNTS,
        "benchmark_status_counts": {"include": 60},
        "evaluation_rules": [
            "This gold file was frozen before the answer candidate was run on any external holdout-v2 question.",
            "Do not modify the frozen answer candidate before the first holdout-v2 prediction and score.",
            "Do not tune the candidate using individual holdout-v2 failures. Any tuning after scoring converts this set into development data.",
            "Primary metric is question-level evidence-status accuracy across all 60 included questions.",
            "Also report per-class evidence-status accuracy and the confusion matrix.",
            "Because each public source post contributes three related questions, also report source-cluster macro accuracy.",
            "For sufficient cases, report any-expected-section citation coverage and all-expected-sections citation coverage.",
            "partial_support_sections are adjudication audit metadata only and must never be exported to the blind predictor.",
        ],
        "questions": frozen_questions,
    }

    OUTPUT_PATH.write_text(
        json.dumps(gold, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    verify = load_json(OUTPUT_PATH)
    if verify.get("status") != "FROZEN_DO_NOT_TUNE_ON_THIS_SET":
        raise RuntimeError("Frozen gold status verification failed.")
    if verify.get("question_count") != 60:
        raise RuntimeError("Frozen gold question count verification failed.")
    if verify.get("evidence_status_counts") != EXPECTED_COUNTS:
        raise RuntimeError("Frozen gold class-count verification failed.")

    print("Waypoint external holdout-v2 adjudication freeze")
    print("=" * 47)
    print(f"Draft:                     {DRAFT_PATH}")
    print(f"Packet:                    {PACKET_PATH}")
    print(f"Output:                    {OUTPUT_PATH}")
    print()
    print(f"Draft SHA256:              {sha256(DRAFT_PATH)}")
    print(f"Packet SHA256:             {sha256(PACKET_PATH)}")
    print(f"Raw holdout SHA256:        {sha256(RAW_PATH)}")
    print(f"Candidate freeze SHA256:   {sha256(FREEZE_PATH)}")
    print(f"ask.py SHA256:             {sha256(ASK_PATH)}")
    print(f"Corpus snapshot SHA256:    {EXPECTED_CORPUS_SNAPSHOT_SHA256}")
    print()
    print("Questions frozen:          60")
    print("Source clusters:           20")
    print("Evidence status counts:")
    print("  sufficient               16")
    print("  corpus_gap               34")
    print("  external_source_required 10")
    print("Benchmark includes:        60")
    print()
    print("Runtime/model calls:       NONE")
    print("Retrieval calls:           NONE")
    print("Reranker calls:            NONE")
    print("Database writes:           NONE")
    print(f"Frozen gold SHA256:        {sha256(OUTPUT_PATH)}")
    print()
    print("External holdout-v2 adjudication freeze: PASS")


if __name__ == "__main__":
    main()
