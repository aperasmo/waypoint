"""Run external-v1 development questions through evidence-adequacy v2.

External v1 is DEVELOPMENT DATA ONLY. Its original blind failures have already
been inspected, so this run must not be described as untouched holdout evidence.

This runner:
- reads only the existing blind external-v1 input;
- requires the active app/api/routes/ask.py to match the exact v2 candidate SHA;
- calls the current production ask() entrypoint;
- never opens adjudication gold;
- never reads expected sections;
- performs no scoring;
- writes to a new v2 development artifact;
- never overwrites earlier blind or development predictions.

Run from backend/:
    uv run python -m py_compile scripts/run_external_dev_v1_predictions_v2.py
    uv run python -m scripts.run_external_dev_v1_predictions_v2

Input:
    tests/external_questions_blind_v1.json

Output:
    tests/external_predictions_dev_v1_evidence_adequacy_v2.json
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from app.api.routes.ask import AskRequest, ask
from app.db.session import dispose_engine, get_session_factory


BACKEND_DIR = Path(__file__).resolve().parent.parent
INPUT_PATH = BACKEND_DIR / "tests" / "external_questions_blind_v1.json"
ASK_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_evidence_adequacy_v2.json"
)

EXPECTED_INPUT_SCHEMA = "waypoint-external-questions-blind-v1"

EXPECTED_ASK_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

ALLOWED_INPUT_CASE_FIELDS = {"case_id", "question"}

ALLOWED_PREDICTION_FIELDS = {
    "case_id",
    "question",
    "interpreted_as",
    "outcome",
    "evidence_status",
    "decision_boundary",
    "answer",
    "citations",
    "missing_information",
    "disclaimer",
}

FORBIDDEN_INPUT_FIELDS = {
    "expected_sections",
    "expected_section",
    "partial_support_sections",
    "benchmark_status",
    "adjudication_note",
    "gold",
    "gold_status",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def validate_blind_input(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise RuntimeError("Blind input root must be an object.")

    if payload.get("schema") != EXPECTED_INPUT_SCHEMA:
        raise RuntimeError(
            f"Unexpected blind input schema: {payload.get('schema')!r}"
        )

    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("Blind input questions must be a list.")

    if payload.get("question_count") != len(questions):
        raise RuntimeError(
            "Blind input question_count does not match questions list."
        )

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    validated: list[dict] = []

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Blind case {index} is not an object.")

        fields = set(item)
        if fields != ALLOWED_INPUT_CASE_FIELDS:
            raise RuntimeError(
                f"Blind case {index} must contain exactly "
                f"{sorted(ALLOWED_INPUT_CASE_FIELDS)}, got {sorted(fields)}."
            )

        leaked = fields & FORBIDDEN_INPUT_FIELDS
        if leaked:
            raise RuntimeError(
                f"Blind case {index} contains forbidden gold fields: "
                f"{sorted(leaked)}"
            )

        case_id = item.get("case_id")
        question = item.get("question")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(f"Blind case {index} has invalid case_id.")
        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(f"Blind case {index} has invalid question.")

        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate blind case_id: {case_id}")
        if question.strip() in seen_questions:
            raise RuntimeError(
                f"Duplicate blind question: {question.strip()!r}"
            )

        seen_ids.add(case_id)
        seen_questions.add(question.strip())

        validated.append(
            {
                "case_id": case_id,
                "question": question.strip(),
            }
        )

    return validated


def serialise_response(case_id: str, response) -> dict:
    citations = [
        {
            "section_code": citation.section_code,
            "title": citation.title,
            "source_url": citation.source_url,
            "effective_date": citation.effective_date,
        }
        for citation in response.citations
    ]

    prediction = {
        "case_id": case_id,
        "question": response.question,
        "interpreted_as": response.interpreted_as,
        "outcome": response.outcome,
        "evidence_status": response.evidence_status,
        "decision_boundary": response.decision_boundary,
        "answer": response.answer,
        "citations": citations,
        "missing_information": list(response.missing_information),
        "disclaimer": response.disclaimer,
    }

    if set(prediction) != ALLOWED_PREDICTION_FIELDS:
        raise RuntimeError(
            f"{case_id}: prediction field shape changed unexpectedly."
        )

    return prediction


async def main() -> None:
    if not INPUT_PATH.exists():
        raise SystemExit(f"Blind input not found: {INPUT_PATH}")

    if not ASK_PATH.exists():
        raise SystemExit(f"Current ask.py not found: {ASK_PATH}")

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"V2 development output already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite an existing prediction artifact."
        )

    active_ask_sha = sha256(ASK_PATH)

    if active_ask_sha != EXPECTED_ASK_SHA256:
        raise SystemExit(
            "Active app/api/routes/ask.py does not match evidence-adequacy v2.\n"
            f"Expected SHA256: {EXPECTED_ASK_SHA256}\n"
            f"Actual SHA256:   {active_ask_sha}\n"
            "Refusing to run against the wrong prompt version."
        )

    blind_payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    questions = validate_blind_input(blind_payload)

    factory = get_session_factory()
    predictions: list[dict] = []

    print("Waypoint external-v1 development prediction v2")
    print("=" * 46)
    print(f"Input:                     {INPUT_PATH}")
    print(f"Current ask.py:            {ASK_PATH}")
    print(f"Current ask.py SHA256:     {active_ask_sha}")
    print(f"Cases:                     {len(questions)}")
    print()
    print("External-v1 status:        DEVELOPMENT ONLY")
    print("Gold file opened:          NO")
    print("Expected sections loaded:  NO")
    print("Scoring performed:         NO")
    print("Production ask pipeline:   YES")
    print()
    print("Running v2 development predictions...")

    try:
        async with factory() as session:
            for index, item in enumerate(questions, start=1):
                request = AskRequest(question=item["question"])
                response = await ask(request, session)

                if response.question != item["question"]:
                    raise RuntimeError(
                        f"{item['case_id']}: production response changed "
                        "the original question field."
                    )

                predictions.append(
                    serialise_response(item["case_id"], response)
                )

                print(
                    f"[{index:>2}/{len(questions)}] "
                    f"{item['case_id']} OK"
                )

        if len(predictions) != len(questions):
            raise RuntimeError(
                "Prediction count does not match blind input count."
            )

        output = {
            "schema": "waypoint-external-predictions-dev-v1-v2",
            "status": "DEVELOPMENT_PREDICTIONS_NOT_UNTOUCHED_HOLDOUT",
            "candidate_name": "evidence_adequacy_v2",
            "source_blind_sha256": sha256(INPUT_PATH),
            "runtime_ask_sha256": active_ask_sha,
            "prediction_count": len(predictions),
            "production_entrypoint": "app.api.routes.ask.ask",
            "predictions": predictions,
        }

        serialised = json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ) + "\n"

        forbidden_output_tokens = (
            '"expected_sections"',
            '"expected_section"',
            '"partial_support_sections"',
            '"benchmark_status"',
            '"adjudication_note"',
        )

        lowered = serialised.lower()
        leaked = [
            token
            for token in forbidden_output_tokens
            if token.lower() in lowered
        ]
        if leaked:
            raise RuntimeError(
                "V2 development prediction artifact unexpectedly contains "
                "gold-only fields: "
                + ", ".join(leaked)
            )

        OUTPUT_PATH.write_text(serialised, encoding="utf-8")

        verify = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))

        if verify.get("runtime_ask_sha256") != active_ask_sha:
            raise RuntimeError("Saved ask.py SHA verification failed.")

        if verify.get("prediction_count") != len(questions):
            raise RuntimeError(
                "Saved prediction count verification failed."
            )

        saved_predictions = verify.get("predictions")
        if not isinstance(saved_predictions, list):
            raise RuntimeError("Saved predictions field is not a list.")

        for index, item in enumerate(saved_predictions, start=1):
            if set(item) != ALLOWED_PREDICTION_FIELDS:
                raise RuntimeError(
                    f"Saved prediction {index} has unexpected fields."
                )

        print()
        print(f"Output:                    {OUTPUT_PATH}")
        print(f"Blind SHA256:              {sha256(INPUT_PATH)}")
        print(f"ask.py SHA256:             {active_ask_sha}")
        print(f"Predictions SHA256:        {sha256(OUTPUT_PATH)}")
        print(f"Predictions completed:     {len(predictions)}/{len(questions)}")
        print()
        print("Gold file opened:          NO")
        print("Expected sections loaded:  NO")
        print("Scoring performed:         NO")
        print("Database writes:           NONE")
        print("External-v1 development prediction v2: PASS")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
