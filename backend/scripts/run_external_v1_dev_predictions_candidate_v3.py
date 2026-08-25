"""Run answer candidate v3 on retired external-v1 development data.

External v1 is DEVELOPMENT / DIAGNOSTIC ONLY. It was already inspected and
used during earlier answer-layer development.

The runner:
- reads only tests/external_questions_blind_v1.json;
- requires active app/api/routes/ask.py to match candidate v3 SHA;
- verifies the historical candidate-v2 development prediction artifact;
- never opens external_adjudication_gold_v1.json;
- performs no scoring;
- writes a new candidate-v3 development prediction artifact;
- refuses to overwrite existing output.

Run from backend/:
    uv run python -m py_compile scripts/run_external_v1_dev_predictions_candidate_v3.py
    uv run python -m scripts.run_external_v1_dev_predictions_candidate_v3

Input:
    tests/external_questions_blind_v1.json

Output:
    tests/external_predictions_dev_v1_candidate_v3.json
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

HISTORICAL_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_evidence_adequacy_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v3.json"
)

EXPECTED_INPUT_SCHEMA = "waypoint-external-questions-blind-v1"

EXPECTED_BLIND_SHA256 = (
    "33C6A0370C382130890681064B4C32C1B"
    "519EF9CF1FC52D7C3D6570C8A60FFCB"
)

EXPECTED_ASK_SHA256 = (
    "F1F17F3C714C956239E4A16BAE48EB8"
    "CFFAA2BB7D7BE809EB182F7D936B008EB"
)

EXPECTED_HISTORICAL_V2_SHA256 = (
    "0F1E84F74DC1B50C6217A1909A48A5FF"
    "922FA537029737E1E8CE3769488FD541"
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Path:     {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing development run."
        )


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")

    return payload


def validate_blind(payload: dict) -> list[dict]:
    if payload.get("schema") != EXPECTED_INPUT_SCHEMA:
        raise RuntimeError(
            f"Unexpected blind schema: {payload.get('schema')!r}"
        )

    questions = payload.get("questions")

    if not isinstance(questions, list):
        raise RuntimeError("Blind questions must be a list.")

    if len(questions) != 51:
        raise RuntimeError(
            f"Expected exactly 51 included v1 questions, got {len(questions)}."
        )

    if payload.get("question_count") != 51:
        raise RuntimeError(
            "Blind metadata question_count is not 51."
        )

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    validated: list[dict] = []

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(f"Blind case {index} is not an object.")

        if set(item) != ALLOWED_INPUT_CASE_FIELDS:
            raise RuntimeError(
                f"Blind case {index} contains unexpected fields: "
                f"{sorted(set(item))}"
            )

        case_id = item.get("case_id")
        question = item.get("question")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                f"Blind case {index} has invalid case_id."
            )

        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(
                f"{case_id}: invalid question."
            )

        cleaned_question = question.strip()

        if case_id in seen_ids:
            raise RuntimeError(f"Duplicate case_id: {case_id}")

        if cleaned_question in seen_questions:
            raise RuntimeError(
                f"Duplicate question: {cleaned_question!r}"
            )

        seen_ids.add(case_id)
        seen_questions.add(cleaned_question)

        validated.append(
            {
                "case_id": case_id,
                "question": cleaned_question,
            }
        )

    return validated


def serialise_response(case_id: str, response) -> dict:
    prediction = {
        "case_id": case_id,
        "question": response.question,
        "interpreted_as": response.interpreted_as,
        "outcome": response.outcome,
        "evidence_status": response.evidence_status,
        "decision_boundary": response.decision_boundary,
        "answer": response.answer,
        "citations": [
            {
                "section_code": citation.section_code,
                "title": citation.title,
                "source_url": citation.source_url,
                "effective_date": citation.effective_date,
            }
            for citation in response.citations
        ],
        "missing_information": list(response.missing_information),
        "disclaimer": response.disclaimer,
    }

    if set(prediction) != ALLOWED_PREDICTION_FIELDS:
        raise RuntimeError(
            f"{case_id}: prediction field shape changed."
        )

    return prediction


async def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Development output already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        INPUT_PATH,
        EXPECTED_BLIND_SHA256,
        "Retired external-v1 blind input",
    )

    require_sha(
        ASK_PATH,
        EXPECTED_ASK_SHA256,
        "Candidate-v3 runtime ask.py",
    )

    require_sha(
        HISTORICAL_V2_PATH,
        EXPECTED_HISTORICAL_V2_SHA256,
        "Historical candidate-v2 development predictions",
    )

    blind = load_json(INPUT_PATH)
    questions = validate_blind(blind)

    historical = load_json(HISTORICAL_V2_PATH)

    if historical.get("status") != (
        "DEVELOPMENT_PREDICTIONS_NOT_UNTOUCHED_HOLDOUT"
    ):
        raise RuntimeError(
            "Historical candidate-v2 artifact is not marked development."
        )

    if historical.get("prediction_count") != 51:
        raise RuntimeError(
            "Historical candidate-v2 prediction count changed."
        )

    factory = get_session_factory()
    predictions: list[dict] = []

    print("Waypoint candidate-v3 external-v1 DEVELOPMENT run")
    print("=" * 49)
    print(f"Input:                     {INPUT_PATH}")
    print(f"Current ask.py:            {ASK_PATH}")
    print(f"Cases:                     {len(questions)}")
    print()
    print(f"Blind SHA256:              {sha256(INPUT_PATH)}")
    print(f"Candidate-v3 ask SHA256:   {sha256(ASK_PATH)}")
    print(
        f"Historical v2 pred SHA256: "
        f"{sha256(HISTORICAL_V2_PATH)}"
    )
    print()
    print("External-v1 status:        DEVELOPMENT / DIAGNOSTIC ONLY")
    print("Gold file opened:          NO")
    print("Expected sections loaded:  NO")
    print("Scoring performed:         NO")
    print("Production ask pipeline:   YES")
    print()
    print("Running candidate v3 on retired external-v1...")

    try:
        async with factory() as session:
            for index, item in enumerate(questions, start=1):
                response = await ask(
                    AskRequest(question=item["question"]),
                    session,
                )

                if response.question != item["question"]:
                    raise RuntimeError(
                        f"{item['case_id']}: response question changed."
                    )

                predictions.append(
                    serialise_response(
                        item["case_id"],
                        response,
                    )
                )

                print(
                    f"[{index:>2}/{len(questions)}] "
                    f"{item['case_id']} OK"
                )

        if len(predictions) != 51:
            raise RuntimeError(
                f"Expected 51 predictions, got {len(predictions)}."
            )

        output = {
            "schema": "waypoint-external-predictions-dev-v1-candidate-v3",
            "status": "DEVELOPMENT_PREDICTIONS_NOT_UNTOUCHED_HOLDOUT",
            "candidate_name": "evidence_adequacy_v3",
            "source_blind_sha256": EXPECTED_BLIND_SHA256,
            "historical_candidate_v2_predictions_sha256": (
                EXPECTED_HISTORICAL_V2_SHA256
            ),
            "runtime_ask_sha256": EXPECTED_ASK_SHA256,
            "prediction_count": len(predictions),
            "production_entrypoint": "app.api.routes.ask.ask",
            "predictions": predictions,
        }

        serialised = json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        ) + "\n"

        for forbidden in (
            '"expected_sections"',
            '"partial_support_sections"',
            '"benchmark_status"',
            '"adjudication_note"',
        ):
            if forbidden.casefold() in serialised.casefold():
                raise RuntimeError(
                    f"Development prediction output contains "
                    f"gold-only field {forbidden}."
                )

        OUTPUT_PATH.write_text(
            serialised,
            encoding="utf-8",
        )

        verify = load_json(OUTPUT_PATH)

        if verify.get("prediction_count") != 51:
            raise RuntimeError(
                "Saved prediction count verification failed."
            )

        if verify.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
            raise RuntimeError(
                "Saved runtime SHA verification failed."
            )

        if verify.get("source_blind_sha256") != EXPECTED_BLIND_SHA256:
            raise RuntimeError(
                "Saved blind SHA verification failed."
            )

        print()
        print(f"Output:                    {OUTPUT_PATH}")
        print(f"Predictions SHA256:        {sha256(OUTPUT_PATH)}")
        print("Predictions completed:     51/51")
        print()
        print("External-v1 status:        DEVELOPMENT / DIAGNOSTIC ONLY")
        print("Gold file opened:          NO")
        print("Expected sections loaded:  NO")
        print("Scoring performed:         NO")
        print("Database writes:           NONE")
        print()
        print("Candidate-v3 external-v1 development run: PASS")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
