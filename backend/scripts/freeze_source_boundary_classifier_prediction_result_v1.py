"""Freeze the first untouched Waypoint source-boundary prediction result.

This script performs NO scoring and makes NO model calls.

It verifies the immutable first-run prediction artifact against the frozen
single-run authorisation and reviewed bundle, records its SHA/counts, and
authorises the separately reviewed scorer.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_prediction_result_v1.py
    uv run python -m scripts.freeze_source_boundary_classifier_prediction_result_v1

Output:
    tests/source_boundary_classifier_prediction_result_v1.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

PACK_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v3.json"
)

THRESHOLDS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v1.json"
)

BUNDLE_REVIEW_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_bundle_review_v1.json"
)

AUTHORISATION_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_run_authorisation_v1.json"
)

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v1.json"
)

SCORER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "score_source_boundary_classifier_contract_v1.py"
)

SCORE_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_v1.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_prediction_result_v1.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_PACK_SHA256 = (
    "C820489715EA3F54138023D680D04DFBF"
    "F5575A515B936FA8C2241E2EA5B219D"
)

EXPECTED_THRESHOLDS_SHA256 = (
    "5E8AFBFFEE5880DEBF4FA6B0A6514E8C"
    "6702F5D9E74D620BA4C1575F49CAC03C"
)

EXPECTED_BUNDLE_REVIEW_SHA256 = (
    "70A532977D0AAE2AD227A594D8EAC3542"
    "D970CB25DA894145E7839E818488527"
)

EXPECTED_AUTHORISATION_SHA256 = (
    "475DB1C7461626566F90C7F7F5BF3DDE"
    "8D8429709B1126B931FE0119AD54808E"
)

EXPECTED_PREDICTIONS_SHA256 = (
    "F9E753BE55B5A06FC09C002962BE82A92"
    "1097D1F94843B63D7E58123661D9DF4"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "BC77C28033F74E3092C8428DE623293D"
    "266FBDEE7FFC237EE79C8AB6F79DE9F3"
)

EXPECTED_RUNNER_SHA256 = (
    "CE2709C654E576B56520AAD7CA9DB90A"
    "88E80CF775C3B8AC7A3864669F610FEF"
)

EXPECTED_SCORER_SHA256 = (
    "19563B4DD326CCB1E5DA125F30625915"
    "FB2BE197786640FA6223BFB44855FE46"
)

EXPECTED_MODEL = "gpt-5.4-mini"
EXPECTED_REASONING_EFFORT = "none"
EXPECTED_MAX_COMPLETION_TOKENS = 800
EXPECTED_CASE_COUNT = 34
EXPECTED_MODEL_CALL_ATTEMPTS = 34
EXPECTED_COMPLETED_PREDICTIONS = 32
EXPECTED_ERRORS = 2


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(
    path: Path,
    expected: str,
    label: str,
) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Path:     {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze first prediction result."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Prediction-result freeze already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    if SCORE_PATH.exists():
        raise SystemExit(
            f"Score artifact already exists: {SCORE_PATH}\n"
            "Prediction result must be frozen before scoring."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )
    require_sha(
        PACK_PATH,
        EXPECTED_PACK_SHA256,
        "Frozen contract test pack v3",
    )
    require_sha(
        THRESHOLDS_PATH,
        EXPECTED_THRESHOLDS_SHA256,
        "Frozen acceptance thresholds",
    )
    require_sha(
        BUNDLE_REVIEW_PATH,
        EXPECTED_BUNDLE_REVIEW_SHA256,
        "Frozen bundle review v1",
    )
    require_sha(
        AUTHORISATION_PATH,
        EXPECTED_AUTHORISATION_SHA256,
        "Frozen single-run authorisation",
    )
    require_sha(
        PREDICTIONS_PATH,
        EXPECTED_PREDICTIONS_SHA256,
        "First untouched prediction artifact",
    )
    require_sha(
        SCORER_PATH,
        EXPECTED_SCORER_SHA256,
        "Reviewed scorer",
    )

    authorisation = load_json(AUTHORISATION_PATH)
    predictions = load_json(PREDICTIONS_PATH)

    if authorisation.get("schema") != (
        "waypoint-source-boundary-classifier-run-authorisation-v1"
    ):
        raise RuntimeError(
            "Unexpected single-run authorisation schema."
        )

    if authorisation.get("status") != (
        "AUTHORISED_SINGLE_FIRST_CONTRACT_RUN"
    ):
        raise RuntimeError(
            "Single-run authorisation status changed."
        )

    if authorisation.get("single_run_only") is not True:
        raise RuntimeError(
            "Single-run authorisation is not single-run only."
        )

    auth_exec = authorisation.get(
        "frozen_execution",
        {},
    )

    expected_exec = {
        "classifier_sha256": EXPECTED_CLASSIFIER_SHA256,
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "contract_test_pack_sha256": EXPECTED_PACK_SHA256,
        "acceptance_thresholds_sha256": (
            EXPECTED_THRESHOLDS_SHA256
        ),
        "model": EXPECTED_MODEL,
        "reasoning_effort": EXPECTED_REASONING_EFFORT,
        "max_completion_tokens": (
            EXPECTED_MAX_COMPLETION_TOKENS
        ),
        "expected_case_count": EXPECTED_CASE_COUNT,
        "calls_per_case": 1,
        "expected_model_call_attempts": (
            EXPECTED_MODEL_CALL_ATTEMPTS
        ),
        "execution_order": "sequential",
        "automatic_retry": False,
        "repair_call": False,
        "fallback_model": False,
    }

    for key, expected_value in expected_exec.items():
        if auth_exec.get(key) != expected_value:
            raise RuntimeError(
                "Single-run authorisation execution contract changed for "
                f"{key!r}."
            )

    if predictions.get("schema") != (
        "waypoint-source-boundary-classifier-predictions-v1"
    ):
        raise RuntimeError(
            "Unexpected prediction-artifact schema."
        )

    if predictions.get("status") != (
        "FIRST_UNTOUCHED_SYNTHETIC_CONTRACT_RUN"
    ):
        raise RuntimeError(
            "Prediction artifact is not marked as the first untouched run."
        )

    source_artifacts = predictions.get(
        "source_artifacts",
        {},
    )

    expected_prediction_sources = {
        "classifier_sha256": EXPECTED_CLASSIFIER_SHA256,
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "contract_test_pack_sha256": EXPECTED_PACK_SHA256,
        "acceptance_thresholds_sha256": (
            EXPECTED_THRESHOLDS_SHA256
        ),
        "run_authorisation_sha256": (
            EXPECTED_AUTHORISATION_SHA256
        ),
    }

    for key, expected_value in (
        expected_prediction_sources.items()
    ):
        if source_artifacts.get(key) != expected_value:
            raise RuntimeError(
                "Prediction artifact source binding changed for "
                f"{key!r}."
            )

    model_config = predictions.get(
        "model_configuration",
        {},
    )

    expected_model_config = {
        "model": EXPECTED_MODEL,
        "reasoning_effort": EXPECTED_REASONING_EFFORT,
        "max_completion_tokens": (
            EXPECTED_MAX_COMPLETION_TOKENS
        ),
        "temperature": 0,
        "response_format": "json_object",
        "automatic_retry": False,
        "repair_call": False,
        "fallback_model": False,
    }

    for key, expected_value in (
        expected_model_config.items()
    ):
        if model_config.get(key) != expected_value:
            raise RuntimeError(
                "Prediction model configuration changed for "
                f"{key!r}."
            )

    counts = predictions.get("counts")

    if not isinstance(counts, dict):
        raise RuntimeError(
            "Prediction artifact is missing counts."
        )

    expected_counts = {
        "case_count": EXPECTED_CASE_COUNT,
        "model_call_attempts": (
            EXPECTED_MODEL_CALL_ATTEMPTS
        ),
        "completed_predictions": (
            EXPECTED_COMPLETED_PREDICTIONS
        ),
        "errors": EXPECTED_ERRORS,
    }

    for key, expected_value in expected_counts.items():
        if counts.get(key) != expected_value:
            raise RuntimeError(
                "Prediction count differs from first-run console result for "
                f"{key!r}.\n"
                f"Expected: {expected_value}\n"
                f"Actual:   {counts.get(key)!r}"
            )

    records = predictions.get("predictions")

    if not isinstance(records, list):
        raise RuntimeError(
            "Prediction records must be a list."
        )

    if len(records) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CASE_COUNT} prediction records; "
            f"found {len(records)}."
        )

    statuses = [
        record.get("status")
        for record in records
        if isinstance(record, dict)
    ]

    if len(statuses) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            "One or more prediction records is not an object."
        )

    if statuses.count("prediction") != (
        EXPECTED_COMPLETED_PREDICTIONS
    ):
        raise RuntimeError(
            "Prediction-record completed count does not match frozen count."
        )

    if statuses.count("error") != EXPECTED_ERRORS:
        raise RuntimeError(
            "Prediction-record error count does not match frozen count."
        )

    if any(
        status not in {"prediction", "error"}
        for status in statuses
    ):
        raise RuntimeError(
            "Prediction artifact contains unknown record status."
        )

    # Do not inspect expected/gold data here. This freeze deliberately
    # records execution facts only.
    result = {
        "schema": (
            "waypoint-source-boundary-classifier-prediction-result-v1"
        ),
        "status": (
            "FROZEN_FIRST_UNTOUCHED_PREDICTION_RESULT"
        ),
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "contract_test_pack_v3_sha256": (
                EXPECTED_PACK_SHA256
            ),
            "acceptance_thresholds_v1_sha256": (
                EXPECTED_THRESHOLDS_SHA256
            ),
            "bundle_review_v1_sha256": (
                EXPECTED_BUNDLE_REVIEW_SHA256
            ),
            "run_authorisation_v1_sha256": (
                EXPECTED_AUTHORISATION_SHA256
            ),
            "classifier_sha256": (
                EXPECTED_CLASSIFIER_SHA256
            ),
            "runner_sha256": EXPECTED_RUNNER_SHA256,
            "scorer_sha256": EXPECTED_SCORER_SHA256,
            "prediction_sha256": (
                EXPECTED_PREDICTIONS_SHA256
            ),
        },
        "execution_result": {
            "model": EXPECTED_MODEL,
            "reasoning_effort": (
                EXPECTED_REASONING_EFFORT
            ),
            "max_completion_tokens": (
                EXPECTED_MAX_COMPLETION_TOKENS
            ),
            "temperature": 0,
            "case_count": EXPECTED_CASE_COUNT,
            "model_call_attempts": (
                EXPECTED_MODEL_CALL_ATTEMPTS
            ),
            "completed_predictions": (
                EXPECTED_COMPLETED_PREDICTIONS
            ),
            "errors": EXPECTED_ERRORS,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "scoring_performed_before_freeze": False,
        },
        "methodological_status": {
            "first_run_completed": True,
            "first_run_prediction_artifact_immutable": True,
            "prediction_artifact_must_not_be_overwritten": True,
            "prediction_set_is_now_observed": True,
            "thresholds_were_frozen_before_prediction": True,
            "gold_or_expected_labels_read_by_this_freeze": False,
            "correctness_metrics_computed_by_this_freeze": False,
            "error_cases_interpreted_by_this_freeze": False,
        },
        "authorisations": {
            "reviewed_scorer_run_authorised": True,
            "classifier_model_prediction_authorised": False,
            "repeat_contract_prediction_run_authorised": False,
            "prediction_artifact_overwrite_authorised": False,
            "threshold_change_authorised": False,
            "contract_pack_change_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "score_source_boundary_classifier_contract_v1"
            ),
            "authorised": True,
            "model_calls": 0,
            "command": (
                "uv run python -m "
                "scripts.score_source_boundary_classifier_contract_v1"
            ),
            "purpose": (
                "Score the frozen first untouched prediction artifact "
                "against the approved contract pack and pre-frozen "
                "acceptance thresholds."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_PREDICTION_RESULT"
    ):
        raise RuntimeError(
            "Saved prediction-result status changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get(
        "reviewed_scorer_run_authorised"
    ) is not True:
        raise RuntimeError(
            "Prediction-result freeze does not authorise scorer."
        )

    for forbidden in (
        "classifier_model_prediction_authorised",
        "repeat_contract_prediction_run_authorised",
        "prediction_artifact_overwrite_authorised",
        "threshold_change_authorised",
        "contract_pack_change_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                "Prediction-result freeze unexpectedly enables: "
                f"{forbidden}"
            )

    print("Waypoint source-boundary first prediction-result freeze")
    print("=" * 59)
    print(
        f"Prediction SHA256:          "
        f"{sha256(PREDICTIONS_PATH)}"
    )
    print(
        f"Authorisation SHA256:       "
        f"{sha256(AUTHORISATION_PATH)}"
    )
    print(
        f"Classifier SHA256:          "
        f"{EXPECTED_CLASSIFIER_SHA256}"
    )
    print(
        f"Runner SHA256:              "
        f"{EXPECTED_RUNNER_SHA256}"
    )
    print(
        f"Scorer SHA256:              "
        f"{sha256(SCORER_PATH)}"
    )
    print()
    print("First untouched execution")
    print("-" * 59)
    print("Cases:                      34")
    print("Model-call attempts:        34")
    print("Completed predictions:      32")
    print("Errors:                     2")
    print("Automatic retry:            NO")
    print("Repair call:                NO")
    print("Fallback model:             NO")
    print()
    print("Scoring performed:          NO")
    print("Gold labels read:           NO")
    print("Correctness interpreted:    NO")
    print()
    print("Prediction artifact:        FROZEN / IMMUTABLE")
    print("Repeat prediction run:      NOT AUTHORISED")
    print("Threshold changes:          NOT AUTHORISED")
    print("Contract-pack changes:      NOT AUTHORISED")
    print()
    print("Reviewed scorer run:        AUTHORISED")
    print("Scorer model calls:         0")
    print()
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  SCORE FROZEN PREDICTIONS")
    print(
        "Command:                    uv run python -m "
        "scripts.score_source_boundary_classifier_contract_v1"
    )
    print()
    print(
        f"Output:                     "
        f"{OUTPUT_PATH}"
    )
    print(
        f"Prediction-result SHA256:   "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("First prediction-result freeze: PASS")


if __name__ == "__main__":
    main()
