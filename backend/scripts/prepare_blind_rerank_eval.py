"""Create a blind reranking question set with all gold labels removed."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = BACKEND_DIR / "tests" / "eval_questions_adjudicated_v2.json"
DEFAULT_OUTPUT = BACKEND_DIR / "tests" / "rerank_questions_blind_v2.json"


def make_case_id(question: str) -> str:
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    return f"q_{digest[:16]}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a question-only blind reranking evaluation set."
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    if not args.source.exists():
        parser.error(f"source benchmark not found: {args.source}")

    if args.output.exists():
        raise SystemExit(
            f"Output already exists: {args.output}\n"
            "Delete it deliberately before regenerating."
        )

    payload = json.loads(args.source.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise SystemExit("Unexpected benchmark schema: root must be an object.")

    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise SystemExit(
            "Unexpected benchmark schema: expected a 'questions' list."
        )

    blind_cases: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    seen_questions: set[str] = set()

    for index, case in enumerate(questions, start=1):
        if not isinstance(case, dict):
            raise SystemExit(f"Question {index} is not an object.")

        question = case.get("question")
        if not isinstance(question, str) or not question.strip():
            raise SystemExit(
                f"Question {index} has no valid non-empty 'question' field."
            )

        question = question.strip()

        if question in seen_questions:
            raise SystemExit(f"Duplicate question text found: {question!r}")

        case_id = make_case_id(question)
        if case_id in seen_ids:
            raise SystemExit(
                f"Deterministic case_id collision for question: {question!r}"
            )

        blind_cases.append({"case_id": case_id, "question": question})
        seen_questions.add(question)
        seen_ids.add(case_id)

    blind_payload = {
        "schema": "waypoint-rerank-blind-v1",
        "source_question_count": len(blind_cases),
        "questions": blind_cases,
    }

    serialised = json.dumps(
        blind_payload,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    # Fail closed if gold/evaluation fields leaked into blind output.
    forbidden_tokens = (
        '"expected_sections"',
        '"expected_section"',
        '"gold"',
        '"answer"',
        '"label"',
    )
    lowered = serialised.lower()
    leaked = [token for token in forbidden_tokens if token.lower() in lowered]
    if leaked:
        raise RuntimeError(
            "Blind export contains forbidden evaluation fields: "
            + ", ".join(leaked)
        )

    args.output.write_text(serialised, encoding="utf-8")

    # Re-read and verify the exact output schema.
    verify = json.loads(args.output.read_text(encoding="utf-8"))
    allowed_root = {"schema", "source_question_count", "questions"}
    if set(verify) != allowed_root:
        raise RuntimeError(
            f"Unexpected blind root fields: {sorted(set(verify) - allowed_root)}"
        )

    for case in verify["questions"]:
        if set(case) != {"case_id", "question"}:
            raise RuntimeError(
                "Blind question contains fields other than "
                "'case_id' and 'question'."
            )

    print("Waypoint blind rerank eval export")
    print("=" * 34)
    print(f"Source:     {args.source}")
    print(f"Output:     {args.output}")
    print(f"Questions:  {len(blind_cases)}")
    print()
    print("Allowed per-case fields:")
    print("  case_id")
    print("  question")
    print()
    print("Gold-label fields exported: none")
    print("Blind export verification: PASS")


if __name__ == "__main__":
    main()