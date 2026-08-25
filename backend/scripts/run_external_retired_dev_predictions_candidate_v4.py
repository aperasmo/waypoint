"""Run candidate v4 on both RETIRED external development sets.

This is DEVELOPMENT / DIAGNOSTIC ONLY.

The runner deliberately executes external-v1 and external-v2 in the same
prediction pass before any scoring. Both datasets are already retired and may
be used for development, but neither result is fresh generalisation evidence.

Candidate v4 is imported directly from _candidates/. Production ask.py must
remain the frozen candidate-v2 runtime and is not replaced.

The runner:
- reads only blind question files;
- never opens either gold adjudication file;
- never loads expected sections or adjudication notes;
- verifies historical prediction artifacts;
- imports the exact candidate-v4 source by SHA;
- uses the existing production retrieval/database stack;
- performs no scoring;
- refuses to overwrite output artifacts.

Run from backend/:
    uv run python -m py_compile scripts/run_external_retired_dev_predictions_candidate_v4.py
    uv run python -m scripts.run_external_retired_dev_predictions_candidate_v4

Inputs:
    tests/external_questions_blind_v1.json
    tests/external_questions_blind_v2.json
    _candidates/ask_factorised_evidence_candidate_v4.py

Outputs:
    tests/external_predictions_dev_v1_candidate_v4.json
    tests/external_predictions_dev_v2_candidate_v4.json
"""

from __future__ import annotations

import asyncio
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

from app.db.session import dispose_engine, get_session_factory


BACKEND_DIR = Path(__file__).resolve().parent.parent

CANDIDATE_PATH = (
    BACKEND_DIR
    / "_candidates"
    / "ask_factorised_evidence_candidate_v4.py"
)

PRODUCTION_ASK_PATH = (
    BACKEND_DIR
    / "app"
    / "api"
    / "routes"
    / "ask.py"
)

V1_BLIND_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_questions_blind_v1.json"
)

V2_BLIND_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_questions_blind_v2.json"
)

V1_BASELINE_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_evidence_adequacy_v2.json"
)

V2_BASELINE_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_blind_v2.json"
)

V1_OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v4.json"
)

V2_OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v2_candidate_v4.json"
)

EXPECTED_CANDIDATE_SHA256 = (
    "F6056EAD183FFDCF19EEE386AA470C6C"
    "EA01C649F18C3C1D87C251689D78C8E8"
)

EXPECTED_PRODUCTION_V2_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_V1_BLIND_SHA256 = (
    "33C6A0370C382130890681064B4C32C1B"
    "519EF9CF1FC52D7C3D6570C8A60FFCB"
)

EXPECTED_V2_BLIND_SHA256 = (
    "9A0D08AD48D49D6F83509F57251AD191"
    "BEAE1BF5DE05D680670BFA46961B1FED"
)

EXPECTED_V1_BASELINE_SHA256 = (
    "0F1E84F74DC1B50C6217A1909A48A5FF"
    "922FA537029737E1E8CE3769488FD541"
)

EXPECTED_V2_BASELINE_SHA256 = (
    "BCC045922577E84AA89CBBE19587E56C"
    "634ABEB119F9476191B050FB2459493D"
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
        raise RuntimeError(
            f"{path.name}: JSON root must be an object."
        )

    return payload


def validate_blind(
    payload: dict,
    *,
    expected_schema: str,
    expected_count: int,
    label: str,
) -> list[dict]:
    if payload.get("schema") != expected_schema:
        raise RuntimeError(
            f"{label}: unexpected schema {payload.get('schema')!r}."
        )

    questions = payload.get("questions")

    if not isinstance(questions, list):
        raise RuntimeError(
            f"{label}: questions must be a list."
        )

    if len(questions) != expected_count:
        raise RuntimeError(
            f"{label}: expected {expected_count} questions, "
            f"got {len(questions)}."
        )

    if payload.get("question_count") != expected_count:
        raise RuntimeError(
            f"{label}: question_count metadata changed."
        )

    seen_ids: set[str] = set()
    seen_questions: set[str] = set()
    validated: list[dict] = []

    for index, item in enumerate(questions, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"{label}: case {index} is not an object."
            )

        if set(item) != ALLOWED_INPUT_CASE_FIELDS:
            raise RuntimeError(
                f"{label}: case {index} has unexpected fields: "
                f"{sorted(set(item))}"
            )

        case_id = item.get("case_id")
        question = item.get("question")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                f"{label}: case {index} has invalid case_id."
            )

        if not isinstance(question, str) or not question.strip():
            raise RuntimeError(
                f"{label}: {case_id} has invalid question."
            )

        cleaned_question = question.strip()

        if case_id in seen_ids:
            raise RuntimeError(
                f"{label}: duplicate case_id {case_id}."
            )

        if cleaned_question in seen_questions:
            raise RuntimeError(
                f"{label}: duplicate question "
                f"{cleaned_question!r}."
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


def load_candidate() -> ModuleType:
    module_name = "waypoint_candidate_v4_dev"

    spec = importlib.util.spec_from_file_location(
        module_name,
        CANDIDATE_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            f"Could not create import spec for {CANDIDATE_PATH}."
        )

    module = importlib.util.module_from_spec(spec)

    # Dynamic modules using postponed annotations must be registered before
    # execution so Pydantic can resolve type aliases from the module namespace.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise

    for required in (
        "AskRequest",
        "AskResponse",
        "ask",
        "_derive_evidence_status",
    ):
        if not hasattr(module, required):
            raise RuntimeError(
                f"Candidate v4 is missing required symbol: {required}"
            )

    return module


def serialise_response(
    case_id: str,
    response,
) -> dict:
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
        "missing_information": list(
            response.missing_information
        ),
        "disclaimer": response.disclaimer,
    }

    if set(prediction) != ALLOWED_PREDICTION_FIELDS:
        raise RuntimeError(
            f"{case_id}: prediction field shape changed."
        )

    return prediction


async def run_dataset(
    *,
    candidate: ModuleType,
    questions: list[dict],
    output_path: Path,
    schema: str,
    dataset_name: str,
    blind_sha: str,
    baseline_sha: str,
    baseline_link_field: str,
) -> None:
    factory = get_session_factory()
    predictions: list[dict] = []

    print()
    print(
        f"Running candidate v4 on {dataset_name} "
        "(RETIRED DEVELOPMENT DATA)"
    )

    async with factory() as session:
        for index, item in enumerate(questions, start=1):
            response = await candidate.ask(
                candidate.AskRequest(
                    question=item["question"]
                ),
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

    if len(predictions) != len(questions):
        raise RuntimeError(
            f"{dataset_name}: prediction count mismatch."
        )

    output = {
        "schema": schema,
        "status": (
            "DEVELOPMENT_PREDICTIONS_NOT_UNTOUCHED_HOLDOUT"
        ),
        "candidate_name": (
            "factorised_evidence_adjudication_v4"
        ),
        "candidate_source_sha256": (
            EXPECTED_CANDIDATE_SHA256
        ),
        "production_runtime_sha256": (
            EXPECTED_PRODUCTION_V2_SHA256
        ),
        "source_blind_sha256": blind_sha,
        baseline_link_field: baseline_sha,
        "prediction_count": len(predictions),
        "candidate_entrypoint": (
            "_candidates/"
            "ask_factorised_evidence_candidate_v4.py:ask"
        ),
        "production_runtime_replaced": False,
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
        '"gold_evidence_status"',
    ):
        if forbidden.casefold() in serialised.casefold():
            raise RuntimeError(
                f"{dataset_name}: output contains "
                f"gold-only field {forbidden}."
            )

    output_path.write_text(
        serialised,
        encoding="utf-8",
    )

    verify = load_json(output_path)

    if verify.get("prediction_count") != len(questions):
        raise RuntimeError(
            f"{dataset_name}: saved count verification failed."
        )

    if verify.get(
        "candidate_source_sha256"
    ) != EXPECTED_CANDIDATE_SHA256:
        raise RuntimeError(
            f"{dataset_name}: saved candidate SHA changed."
        )

    if verify.get(
        "production_runtime_replaced"
    ) is not False:
        raise RuntimeError(
            f"{dataset_name}: output incorrectly says "
            "production was replaced."
        )

    print(
        f"{dataset_name} output SHA256: "
        f"{sha256(output_path)}"
    )


async def main() -> None:
    for output_path in (
        V1_OUTPUT_PATH,
        V2_OUTPUT_PATH,
    ):
        if output_path.exists():
            raise SystemExit(
                f"Development output already exists: "
                f"{output_path}\n"
                "Refusing to overwrite either artifact."
            )

    require_sha(
        CANDIDATE_PATH,
        EXPECTED_CANDIDATE_SHA256,
        "Candidate v4 source",
    )

    require_sha(
        PRODUCTION_ASK_PATH,
        EXPECTED_PRODUCTION_V2_SHA256,
        "Frozen production candidate-v2 ask.py",
    )

    require_sha(
        V1_BLIND_PATH,
        EXPECTED_V1_BLIND_SHA256,
        "Retired external-v1 blind questions",
    )

    require_sha(
        V2_BLIND_PATH,
        EXPECTED_V2_BLIND_SHA256,
        "Retired external-v2 blind questions",
    )

    require_sha(
        V1_BASELINE_PATH,
        EXPECTED_V1_BASELINE_SHA256,
        "Historical candidate-v2 v1 predictions",
    )

    require_sha(
        V2_BASELINE_PATH,
        EXPECTED_V2_BASELINE_SHA256,
        "Historical untouched v2 predictions",
    )

    v1_blind = load_json(V1_BLIND_PATH)
    v2_blind = load_json(V2_BLIND_PATH)

    v1_questions = validate_blind(
        v1_blind,
        expected_schema=(
            "waypoint-external-questions-blind-v1"
        ),
        expected_count=51,
        label="external-v1",
    )

    v2_questions = validate_blind(
        v2_blind,
        expected_schema=(
            "waypoint-external-questions-blind-v2"
        ),
        expected_count=60,
        label="external-v2",
    )

    candidate = load_candidate()

    print(
        "Waypoint candidate-v4 retired external "
        "DEVELOPMENT prediction run"
    )
    print("=" * 61)
    print(
        f"Candidate SHA256:          "
        f"{sha256(CANDIDATE_PATH)}"
    )
    print(
        f"Production v2 SHA256:      "
        f"{sha256(PRODUCTION_ASK_PATH)}"
    )
    print(
        f"External-v1 cases:         "
        f"{len(v1_questions)}"
    )
    print(
        f"External-v2 cases:         "
        f"{len(v2_questions)}"
    )
    print(
        f"Combined cases:            "
        f"{len(v1_questions) + len(v2_questions)}"
    )
    print()
    print(
        "Production ask.py changed: NO"
    )
    print(
        "Gold files opened:         NO"
    )
    print(
        "Expected sections loaded:  NO"
    )
    print(
        "Scoring performed:         NO"
    )
    print(
        "Runtime eval-data access:  NO"
    )

    try:
        await run_dataset(
            candidate=candidate,
            questions=v1_questions,
            output_path=V1_OUTPUT_PATH,
            schema=(
                "waypoint-external-predictions-"
                "dev-v1-candidate-v4"
            ),
            dataset_name="external-v1",
            blind_sha=EXPECTED_V1_BLIND_SHA256,
            baseline_sha=EXPECTED_V1_BASELINE_SHA256,
            baseline_link_field=(
                "historical_candidate_v2_predictions_sha256"
            ),
        )

        await run_dataset(
            candidate=candidate,
            questions=v2_questions,
            output_path=V2_OUTPUT_PATH,
            schema=(
                "waypoint-external-predictions-"
                "dev-v2-candidate-v4"
            ),
            dataset_name="external-v2",
            blind_sha=EXPECTED_V2_BLIND_SHA256,
            baseline_sha=EXPECTED_V2_BASELINE_SHA256,
            baseline_link_field=(
                "historical_first_predictions_sha256"
            ),
        )

        print()
        print("Outputs:")
        print(f"  {V1_OUTPUT_PATH}")
        print(f"  {V2_OUTPUT_PATH}")
        print()
        print("Predictions completed:     111/111")
        print(
            "External v1/v2 status:     "
            "DEVELOPMENT / DIAGNOSTIC ONLY"
        )
        print("Gold files opened:         NO")
        print("Scoring performed:         NO")
        print("Production ask.py changed: NO")
        print("Database writes:           NONE")
        print()
        print(
            "Candidate-v4 retired development "
            "prediction run: PASS"
        )

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())
