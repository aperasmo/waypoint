"""Create an adjudicated v2 of Waypoint's frozen retrieval eval set.

The existing tests/eval_questions.json is never modified.

Exactly two questions are adjudicated from passage inspection:

1. "do I need a police clearance"
   A5.10 -> A5.5 + A5.10

2. "I have 6 points can I apply for residence"
   SR3.15 + SR3.20 -> SR3.5 + SR3.10

The script fails closed if the source file does not contain the exact
pre-adjudication labels expected here. All other question objects are
preserved byte-for-byte at the parsed JSON-value level.

Run from backend/:
    uv run python -m scripts.create_eval_adjudicated_v2
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
SOURCE_PATH = BACKEND_DIR / "tests" / "eval_questions.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "eval_questions_adjudicated_v2.json"

ADJUDICATIONS = {
    "do I need a police clearance": {
        "before": ["A5.10"],
        "after": ["A5.5", "A5.10"],
        "reason": (
            "A5.5 directly states when police certificates are required; "
            "A5.10 governs police-certificate validity, reuse and exceptions."
        ),
    },
    "I have 6 points can I apply for residence": {
        "before": ["SR3.15", "SR3.20"],
        "after": ["SR3.5", "SR3.10"],
        "reason": (
            "SR3.5 states the conditions for being invited to apply, including "
            "skilled employment and six points; SR3.10 summarises the grant "
            "requirements. SR3.15 and SR3.20 are supporting component rules."
        ),
    },
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    if not SOURCE_PATH.exists():
        raise SystemExit(f"Source eval file not found: {SOURCE_PATH}")

    source = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))

    if not isinstance(source, dict) or not isinstance(source.get("questions"), list):
        raise SystemExit(
            "Unexpected eval schema: expected an object containing a "
            "'questions' list."
        )

    output = deepcopy(source)
    seen: set[str] = set()

    for case in output["questions"]:
        question = case.get("question")
        if question not in ADJUDICATIONS:
            continue

        rule = ADJUDICATIONS[question]
        actual = case.get("expected_sections")

        if actual != rule["before"]:
            raise SystemExit(
                "Adjudication aborted because the source benchmark no longer "
                f"matches the reviewed baseline.\n"
                f"Question: {question}\n"
                f"Expected source value: {rule['before']}\n"
                f"Actual source value:   {actual}"
            )

        case["expected_sections"] = list(rule["after"])
        seen.add(question)

    missing = set(ADJUDICATIONS) - seen
    if missing:
        raise SystemExit(
            "Adjudication aborted. Target question(s) not found:\n"
            + "\n".join(f"- {q}" for q in sorted(missing))
        )

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Output already exists: {OUTPUT_PATH}\n"
            "Delete it deliberately before regenerating."
        )

    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    # Verify only the intended expected_sections values changed.
    source_by_q = {
        case["question"]: case
        for case in source["questions"]
    }
    output_by_q = {
        case["question"]: case
        for case in output["questions"]
    }

    if set(source_by_q) != set(output_by_q):
        raise RuntimeError("Question set changed unexpectedly.")

    changed_questions: list[str] = []

    for question in source_by_q:
        before = deepcopy(source_by_q[question])
        after = deepcopy(output_by_q[question])

        if before == after:
            continue

        changed_questions.append(question)

        before_expected = before.pop("expected_sections", None)
        after_expected = after.pop("expected_sections", None)

        if before != after:
            raise RuntimeError(
                f"Fields other than expected_sections changed for: {question}"
            )

        rule = ADJUDICATIONS.get(question)
        if rule is None:
            raise RuntimeError(
                f"Unexpected question changed: {question}"
            )

        if before_expected != rule["before"] or after_expected != rule["after"]:
            raise RuntimeError(
                f"Unexpected adjudication values for: {question}"
            )

    if set(changed_questions) != set(ADJUDICATIONS):
        raise RuntimeError(
            "Changed-question set does not exactly match the adjudication plan."
        )

    print("Waypoint eval-set adjudication v2")
    print("=" * 34)
    print(f"Source:  {SOURCE_PATH}")
    print(f"Output:  {OUTPUT_PATH}")
    print()
    print(f"Questions preserved:       {len(output['questions'])}")
    print(f"Questions adjudicated:     {len(changed_questions)}")
    print()

    for question in changed_questions:
        rule = ADJUDICATIONS[question]
        print(question)
        print(f"    before: {rule['before']}")
        print(f"    after:  {rule['after']}")
        print(f"    reason: {rule['reason']}")
        print()

    print(f"Source SHA256: {sha256(SOURCE_PATH)}")
    print(f"V2 SHA256:     {sha256(OUTPUT_PATH)}")
    print()
    print("Original benchmark was not modified.")


if __name__ == "__main__":
    main()