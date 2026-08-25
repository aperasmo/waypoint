"""Create the blind external Waypoint evaluation input.

This utility reads the frozen external adjudication gold only to select cases
whose benchmark_status is "include", then emits a blind file containing only:

    case_id
    question

No evidence_status, expected_sections, section codes, platform metadata, or
adjudication notes are exported.

This is evaluation tooling only. Runtime and ranking code must never read the
gold file.

Run from backend/:
    uv run python -m py_compile scripts/prepare_blind_external_eval.py
    uv run python -m scripts.prepare_blind_external_eval

Input:
    tests/external_adjudication_gold_v1.json

Output:
    tests/external_questions_blind_v1.json
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
GOLD_PATH = BACKEND_DIR / "tests" / "external_adjudication_gold_v1.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "external_questions_blind_v1.json"

EXPECTED_GOLD_SCHEMA = "waypoint-external-adjudication-gold-v1"

ALLOWED_OUTPUT_CASE_FIELDS = {"case_id", "question"}

FORBIDDEN_OUTPUT_FIELDS = {
    "evidence_status",
    "expected_sections",
    "expected_section",
    "partial_support_sections",
    "benchmark_status",
    "adjudication_note",
    "platform",
    "community",
    "category",
    "source_url",
    "section_code",
    "section_codes",
    "decision_boundary",
    "outcome",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    if not GOLD_PATH.exists():
        raise SystemExit(f"Frozen gold file not found: {GOLD_PATH}")

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Blind output already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite an existing blind artifact."
        )

    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

    if not isinstance(gold, dict):
        raise RuntimeError("Frozen gold root must be an object.")

    if gold.get("schema") != EXPECTED_GOLD_SCHEMA:
        raise RuntimeError(
            f"Unexpected gold schema: {gold.get('schema')!r}"
        )

    questions = gold.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("Frozen gold questions must be a list.")

    if gold.get("question_count") != len(questions):
        raise RuntimeError(
            "Frozen gold question_count does not match questions list."
        )

    blind_cases: list[dict] = []
    seen_ids: set[str] = set()
    seen_questions: set[str] = set()

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Gold question {index} is not an object.")

        if item.get("benchmark_status") != "include":
            continue

        case_id = item.get("candidate_id")
        question = item.get("question")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                f"Included gold question {index} has invalid candidate_id."
            )
        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(
                f"Included gold question {index} has invalid question."
            )

        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate included case_id: {case_id}")
        if question.strip() in seen_questions:
            raise RuntimeError(
                f"Duplicate included question: {question.strip()!r}"
            )

        seen_ids.add(case_id)
        seen_questions.add(question.strip())

        blind_cases.append(
            {
                "case_id": case_id,
                "question": question.strip(),
            }
        )

    declared_includable = gold.get("benchmark_status_counts", {}).get(
        "include"
    )
    if declared_includable != len(blind_cases):
        raise RuntimeError(
            "Included-case count does not match frozen gold metadata: "
            f"metadata={declared_includable!r}, derived={len(blind_cases)}"
        )

    payload = {
        "schema": "waypoint-external-questions-blind-v1",
        "status": "BLIND_PREDICTION_INPUT",
        "source_gold_sha256": sha256(GOLD_PATH),
        "question_count": len(blind_cases),
        "allowed_case_fields": sorted(ALLOWED_OUTPUT_CASE_FIELDS),
        "questions": blind_cases,
    }

    serialised = json.dumps(
        payload,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    # Fail closed if any adjudication/ranking-answer fields leaked.
    lowered = serialised.lower()
    leaked = [
        field
        for field in FORBIDDEN_OUTPUT_FIELDS
        if f'"{field.lower()}"' in lowered
    ]
    if leaked:
        raise RuntimeError(
            "Blind output unexpectedly contains forbidden fields: "
            + ", ".join(sorted(leaked))
        )

    OUTPUT_PATH.write_text(serialised, encoding="utf-8")

    # Re-read and verify exact per-case field shape.
    verify = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

    if verify.get("question_count") != len(blind_cases):
        raise RuntimeError("Blind question count verification failed.")

    for index, item in enumerate(verify.get("questions", []), start=1):
        fields = set(item)
        if fields != ALLOWED_OUTPUT_CASE_FIELDS:
            raise RuntimeError(
                f"Blind case {index} has unexpected fields: "
                f"{sorted(fields)}"
            )

    print("Waypoint blind external evaluation export")
    print("=" * 41)
    print(f"Gold:                      {GOLD_PATH}")
    print(f"Output:                    {OUTPUT_PATH}")
    print()
    print(f"Frozen gold questions:     {len(questions)}")
    print(f"Blind included questions:  {len(blind_cases)}")
    print("Allowed per-case fields:")
    print("  case_id")
    print("  question")
    print()
    print(f"Gold SHA256:               {sha256(GOLD_PATH)}")
    print(f"Blind SHA256:              {sha256(OUTPUT_PATH)}")
    print()
    print("Gold labels exported:      none")
    print("Section codes exported:    none")
    print("Adjudication fields:       none")
    print("Runtime/model calls:       NONE")
    print("Database writes:           NONE")
    print("Blind external export:     PASS")


if __name__ == "__main__":
    main()
