"""Run the frozen Waypoint answer candidate once on external holdout v2.

This is the FIRST and ONLY untouched prediction run for external holdout v2.

The runner:
- reads only tests/external_questions_blind_v2.json;
- requires the active app/api/routes/ask.py to match the frozen candidate SHA;
- requires the blind input to match its frozen SHA;
- calls the production ask() entrypoint;
- never opens external_adjudication_gold_v2.json;
- never reads expected sections or adjudication notes;
- performs no scoring;
- writes a new immutable prediction artifact;
- refuses to overwrite an existing prediction artifact.

Run from backend/:
    uv run python -m py_compile scripts/run_external_holdout_v2_predictions.py
    uv run python -m scripts.run_external_holdout_v2_predictions

Input:
    tests/external_questions_blind_v2.json

Output:
    tests/external_predictions_blind_v2.json
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from pathlib import Path

from app.api.routes.ask import AskRequest, ask
from app.db.session import dispose_engine, get_session_factory


BACKEND_DIR = Path(__file__).resolve().parent.parent

INPUT_PATH = BACKEND_DIR / "tests" / "external_questions_blind_v2.json"
ASK_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
FREEZE_PATH = BACKEND_DIR / "tests" / "answer_candidate_v2_freeze.json"

OUTPUT_PATH = BACKEND_DIR / "tests" / "external_predictions_blind_v2.json"

EXPECTED_INPUT_SCHEMA = "waypoint-external-questions-blind-v2"
EXPECTED_INPUT_STATUS = "FROZEN_BLIND_UNSCORED_HOLDOUT_V2"

EXPECTED_BLIND_SHA256 = (
    "9A0D08AD48D49D6F83509F57251AD191"
    "BEAE1BF5DE05D680670BFA46961B1FED"
)

EXPECTED_ASK_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_CANDIDATE_FREEZE_SHA256 = (
    "0600D79FFC375C7CC8FC358722EE51A9"
    "8B0D979188F61FF8B4CBD7412A1CB03C"
)

EXPECTED_GOLD_SHA256 = (
    "D584326117A4CEF64C869225AD9186FF"
    "95C1D0753ED93706A0748C6ABCC4FA36"
)

ALLOWED_INPUT_CASE_FIELDS = {"case_id", "question"}

FORBIDDEN_INPUT_FIELDS = {
    "evidence_status",
    "expected_sections",
    "expected_section",
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


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: JSON root must be an object.")

    return payload


def validate_blind_input(payload: object) -> list[dict]:
    if not isinstance(payload, dict):
        raise RuntimeError("Blind input root must be an object.")

    if payload.get("schema") != EXPECTED_INPUT_SCHEMA:
        raise RuntimeError(
            f"Unexpected blind input schema: {payload.get('schema')!r}"
        )

    if payload.get("status") != EXPECTED_INPUT_STATUS:
        raise RuntimeError(
            f"Unexpected blind input status: {payload.get('status')!r}"
        )

    if payload.get("source_gold_sha256") != EXPECTED_GOLD_SHA256:
        raise RuntimeError(
            "Blind input is not linked to the expected frozen gold SHA."
        )

    if payload.get("candidate_freeze_sha256") != EXPECTED_CANDIDATE_FREEZE_SHA256:
        raise RuntimeError(
            "Blind input is not linked to the expected candidate freeze."
        )

    if payload.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError(
            "Blind input is not linked to the expected ask.py candidate."
        )

    questions = payload.get("questions")
    if not isinstance(questions, list):
        raise RuntimeError("Blind input questions must be a list.")

    if payload.get("question_count") != len(questions):
        raise RuntimeError(
            "Blind input question_count does not match questions list."
        )

    if len(questions) != 60:
        raise RuntimeError(
            f"Expected exactly 60 blind questions, got {len(questions)}."
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
            raise RuntimeError(
                f"Blind case {index} has invalid case_id."
            )

        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(
                f"Blind case {index} has invalid question."
            )

        cleaned_question = question.strip()

        if case_id in seen_ids:
            raise RuntimeError(
                f"Duplicate blind case_id: {case_id}"
            )

        if cleaned_question in seen_questions:
            raise RuntimeError(
                f"Duplicate blind question: {cleaned_question!r}"
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

    if not FREEZE_PATH.exists():
        raise SystemExit(f"Candidate freeze not found: {FREEZE_PATH}")

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Holdout-v2 prediction output already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite the first untouched prediction artifact."
        )

    if sha256(INPUT_PATH) != EXPECTED_BLIND_SHA256:
        raise SystemExit(
            "Blind input SHA does not match the frozen holdout-v2 file.\n"
            f"Expected: {EXPECTED_BLIND_SHA256}\n"
            f"Actual:   {sha256(INPUT_PATH)}"
        )

    if sha256(ASK_PATH) != EXPECTED_ASK_SHA256:
        raise SystemExit(
            "Active app/api/routes/ask.py does not match the frozen candidate.\n"
            f"Expected: {EXPECTED_ASK_SHA256}\n"
            f"Actual:   {sha256(ASK_PATH)}"
        )

    if sha256(FREEZE_PATH) != EXPECTED_CANDIDATE_FREEZE_SHA256:
        raise SystemExit(
            "Candidate freeze artifact SHA does not match.\n"
            f"Expected: {EXPECTED_CANDIDATE_FREEZE_SHA256}\n"
            f"Actual:   {sha256(FREEZE_PATH)}"
        )

    blind_payload = load_json(INPUT_PATH)
    questions = validate_blind_input(blind_payload)

    freeze = load_json(FREEZE_PATH)

    if freeze.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
        raise RuntimeError(
            "Candidate freeze does not identify the expected ask.py SHA."
        )

    factory = get_session_factory()
    predictions: list[dict] = []

    print("Waypoint external holdout-v2 untouched prediction run")
    print("=" * 50)
    print(f"Input:                     {INPUT_PATH}")
    print(f"Current ask.py:            {ASK_PATH}")
    print(f"Candidate freeze:          {FREEZE_PATH}")
    print(f"Cases:                     {len(questions)}")
    print()
    print(f"Blind SHA256:              {sha256(INPUT_PATH)}")
    print(f"ask.py SHA256:             {sha256(ASK_PATH)}")
    print(f"Candidate freeze SHA256:   {sha256(FREEZE_PATH)}")
    print()
    print("Gold file opened:          NO")
    print("Expected sections loaded:  NO")
    print("Adjudication notes loaded: NO")
    print("Scoring performed:         NO")
    print("Production ask pipeline:   YES")
    print()
    print("Running frozen candidate exactly once...")

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
            "schema": "waypoint-external-predictions-blind-v2",
            "status": "FIRST_UNTOUCHED_HOLDOUT_V2_PREDICTIONS",
            "source_blind_sha256": EXPECTED_BLIND_SHA256,
            "source_gold_sha256_recorded_in_blind": EXPECTED_GOLD_SHA256,
            "candidate_freeze_sha256": EXPECTED_CANDIDATE_FREEZE_SHA256,
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

        forbidden_output_tokens = (
            '"expected_sections"',
            '"expected_section"',
            '"partial_support_sections"',
            '"benchmark_status"',
            '"adjudication_note"',
        )

        lowered = serialised.casefold()
        leaked = [
            token
            for token in forbidden_output_tokens
            if token.casefold() in lowered
        ]

        if leaked:
            raise RuntimeError(
                "Prediction artifact unexpectedly contains gold-only fields: "
                + ", ".join(leaked)
            )

        OUTPUT_PATH.write_text(serialised, encoding="utf-8")

        verify = load_json(OUTPUT_PATH)

        if verify.get("runtime_ask_sha256") != EXPECTED_ASK_SHA256:
            raise RuntimeError(
                "Saved ask.py SHA verification failed."
            )

        if verify.get("source_blind_sha256") != EXPECTED_BLIND_SHA256:
            raise RuntimeError(
                "Saved blind SHA verification failed."
            )

        if verify.get("candidate_freeze_sha256") != (
            EXPECTED_CANDIDATE_FREEZE_SHA256
        ):
            raise RuntimeError(
                "Saved candidate freeze SHA verification failed."
            )

        if verify.get("prediction_count") != len(questions):
            raise RuntimeError(
                "Saved prediction count verification failed."
            )

        saved_predictions = verify.get("predictions")
        if not isinstance(saved_predictions, list):
            raise RuntimeError(
                "Saved predictions field is not a list."
            )

        for index, item in enumerate(saved_predictions, start=1):
            if set(item) != ALLOWED_PREDICTION_FIELDS:
                raise RuntimeError(
                    f"Saved prediction {index} has unexpected fields."
                )

        print()
        print(f"Output:                    {OUTPUT_PATH}")
        print(f"Predictions SHA256:        {sha256(OUTPUT_PATH)}")
        print(f"Predictions completed:     {len(predictions)}/{len(questions)}")
        print()
        print("Gold file opened:          NO")
        print("Expected sections loaded:  NO")
        print("Adjudication notes loaded: NO")
        print("Scoring performed:         NO")
        print("Database writes:           NONE")
        print()
        print("External holdout-v2 untouched prediction run: PASS")

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
