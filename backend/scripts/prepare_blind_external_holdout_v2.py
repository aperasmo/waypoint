"""Create the blind question-only file for external holdout v2.

This script removes all adjudication/gold information before the frozen
candidate is allowed to see the questions.

It does NOT:
- call app.api.routes.ask;
- call retrieval, embeddings, reranking, or an answer model;
- modify runtime code;
- write to the database;
- score anything.

Run from backend/:
    uv run python -m py_compile scripts/prepare_blind_external_holdout_v2.py
    uv run python -m scripts.prepare_blind_external_holdout_v2

Input:
    tests/external_adjudication_gold_v2.json

Output:
    tests/external_questions_blind_v2.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

GOLD_PATH = BACKEND_DIR / "tests" / "external_adjudication_gold_v2.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "external_questions_blind_v2.json"
ASK_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
FREEZE_PATH = BACKEND_DIR / "tests" / "answer_candidate_v2_freeze.json"

EXPECTED_GOLD_SHA256 = "D584326117A4CEF64C869225AD9186FF95C1D0753ED93706A0748C6ABCC4FA36"
EXPECTED_ASK_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)
EXPECTED_CANDIDATE_FREEZE_SHA256 = (
    "0600D79FFC375C7CC8FC358722EE51A9"
    "8B0D979188F61FF8B4CBD7412A1CB03C"
)

EXPECTED_GOLD_SCHEMA = "waypoint-external-adjudication-gold-v2"
EXPECTED_GOLD_STATUS = "FROZEN_DO_NOT_TUNE_ON_THIS_SET"

EXPECTED_COUNTS = {
    "sufficient": 16,
    "corpus_gap": 34,
    "external_source_required": 10,
}

ALLOWED_BLIND_CASE_FIELDS = {"case_id", "question"}

FORBIDDEN_GOLD_FIELDS = {
    "evidence_status",
    "expected_sections",
    "partial_support_sections",
    "benchmark_status",
    "adjudication_note",
    "decision_boundary",
    "outcome",
    "gold",
    "gold_status",
    "source_url",
    "source_title",
    "source_date",
    "platform",
    "community",
    "category",
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
            "Refusing to export blind questions from a changed artifact."
        )


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Blind v2 output already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite an existing blind holdout artifact."
        )

    require_sha(GOLD_PATH, EXPECTED_GOLD_SHA256)
    require_sha(ASK_PATH, EXPECTED_ASK_SHA256)
    require_sha(FREEZE_PATH, EXPECTED_CANDIDATE_FREEZE_SHA256)

    gold = load_json(GOLD_PATH)
    freeze = load_json(FREEZE_PATH)

    if gold.get("schema") != EXPECTED_GOLD_SCHEMA:
        raise RuntimeError(
            f"Unexpected gold schema: {gold.get('schema')!r}"
        )

    if gold.get("status") != EXPECTED_GOLD_STATUS:
        raise RuntimeError(
            f"Unexpected gold status: {gold.get('status')!r}"
        )

    if gold.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError(
            "Gold file is not linked to the expected frozen ask.py."
        )

    if gold.get("candidate_freeze_sha256") != EXPECTED_CANDIDATE_FREEZE_SHA256:
        raise RuntimeError(
            "Gold file is not linked to the expected candidate freeze."
        )

    if freeze.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError(
            "Candidate freeze is not linked to the expected ask.py."
        )

    if gold.get("question_count") != 60:
        raise RuntimeError(
            f"Expected 60 gold questions, got {gold.get('question_count')!r}."
        )

    if gold.get("included_question_count") != 60:
        raise RuntimeError(
            "Expected all 60 v2 questions to remain included."
        )

    if gold.get("unique_source_count") != 20:
        raise RuntimeError(
            "Expected 20 source clusters in frozen gold."
        )

    if gold.get("evidence_status_counts") != EXPECTED_COUNTS:
        raise RuntimeError(
            "Frozen gold evidence-status counts changed."
        )

    questions = gold.get("questions")
    if not isinstance(questions, list) or len(questions) != 60:
        raise RuntimeError(
            "Frozen gold questions must be a 60-item list."
        )

    blind_questions: list[dict] = []
    seen_ids: set[str] = set()
    seen_questions: set[str] = set()

    class_counts: Counter = Counter()

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"Gold question {index} is not an object."
            )

        if item.get("benchmark_status") != "include":
            raise RuntimeError(
                f"{item.get('candidate_id')}: unexpected excluded case."
            )

        status = item.get("evidence_status")
        class_counts[status] += 1

        case_id = item.get("candidate_id")
        question = item.get("question")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                f"Gold question {index} has invalid candidate_id."
            )

        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(
                f"{case_id}: question text is invalid."
            )

        if case_id in seen_ids:
            raise RuntimeError(
                f"Duplicate candidate_id: {case_id}"
            )

        cleaned_question = question.strip()

        if cleaned_question in seen_questions:
            raise RuntimeError(
                f"Duplicate question text: {cleaned_question!r}"
            )

        seen_ids.add(case_id)
        seen_questions.add(cleaned_question)

        blind_questions.append(
            {
                "case_id": case_id,
                "question": cleaned_question,
            }
        )

    if dict(class_counts) != EXPECTED_COUNTS:
        raise RuntimeError(
            "Question-level class counts do not match frozen metadata."
        )

    blind = {
        "schema": "waypoint-external-questions-blind-v2",
        "status": "FROZEN_BLIND_UNSCORED_HOLDOUT_V2",
        "source_gold_sha256": EXPECTED_GOLD_SHA256,
        "candidate_freeze_sha256": EXPECTED_CANDIDATE_FREEZE_SHA256,
        "runtime_ask_sha256": EXPECTED_ASK_SHA256,
        "question_count": len(blind_questions),
        "questions": blind_questions,
    }

    serialised = json.dumps(
        blind,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    lowered = serialised.casefold()

    leaked = [
        field
        for field in sorted(FORBIDDEN_GOLD_FIELDS)
        if f'"{field.casefold()}"' in lowered
    ]

    if leaked:
        raise RuntimeError(
            "Blind export contains forbidden adjudication fields: "
            + ", ".join(leaked)
        )

    OUTPUT_PATH.write_text(serialised, encoding="utf-8")

    verify = load_json(OUTPUT_PATH)

    if verify.get("question_count") != 60:
        raise RuntimeError(
            "Saved blind question count verification failed."
        )

    saved_questions = verify.get("questions")
    if not isinstance(saved_questions, list):
        raise RuntimeError(
            "Saved blind questions field is not a list."
        )

    for index, item in enumerate(saved_questions, start=1):
        if set(item) != ALLOWED_BLIND_CASE_FIELDS:
            raise RuntimeError(
                f"Blind question {index} has unexpected fields: "
                f"{sorted(set(item))}"
            )

    # Confirm question text and IDs were preserved exactly.
    for original, exported in zip(questions, saved_questions):
        if original["candidate_id"] != exported["case_id"]:
            raise RuntimeError(
                "Candidate ID changed during blind export."
            )
        if original["question"].strip() != exported["question"]:
            raise RuntimeError(
                "Question text changed during blind export."
            )

    print("Waypoint external holdout-v2 blind export")
    print("=" * 41)
    print(f"Frozen gold:               {GOLD_PATH}")
    print(f"Output:                    {OUTPUT_PATH}")
    print()
    print(f"Gold SHA256:               {sha256(GOLD_PATH)}")
    print(f"Candidate freeze SHA256:   {sha256(FREEZE_PATH)}")
    print(f"ask.py SHA256:             {sha256(ASK_PATH)}")
    print(f"Blind SHA256:              {sha256(OUTPUT_PATH)}")
    print()
    print("Questions exported:        60")
    print("Question text preserved:   PASS")
    print("Case IDs preserved:        PASS")
    print("Gold labels exported:      NONE")
    print("Expected sections exported:NONE")
    print("Adjudication notes:        NONE")
    print("Source metadata exported:  NONE")
    print("Runtime/model calls:       NONE")
    print("Retrieval/reranker calls:  NONE")
    print("Database writes:           NONE")
    print()
    print("External holdout-v2 blind export: PASS")


if __name__ == "__main__":
    main()
