"""Freeze the first untouched Waypoint classifier prediction result v2.

FREEZE ONLY.
- No model calls.
- No scoring.
- Does not read the gold pack.
- Does not read the acceptance-threshold file.
- Binds the exact first untouched prediction artifact.
- Authorises scoring only after the prediction artifact is frozen.
- Refuses to overwrite an existing freeze or proceed if a score already exists.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_prediction_result_v2.py
    uv run python -m scripts.freeze_source_boundary_classifier_prediction_result_v2

Output:
    tests/source_boundary_classifier_prediction_result_v2.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v2.json"
)

RUN_AUTHORISATION_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_run_authorisation_v2.json"
)

SCORE_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_v2.json"
)

SCORE_RESULT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_result_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_prediction_result_v2.json"
)

EXPECTED_PREDICTION_SHA256 = (
    "7EE68C61443D73B298574A8EB2BBA4425"
    "A99D577F618B7565848F16FEA8C6EF1"
)

EXPECTED_RUN_AUTHORISATION_SHA256 = (
    "566E7E9CAE745588BE7043A0D42CC96D"
    "DA0B95322821C3916409B43B32AE1C80"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "8193FCDDB48585EC8A8BA8BCC477D123"
    "011B50F2F38531BEB2D88836975FF949"
)

EXPECTED_PROMPT_SHA256 = (
    "4A5C725B528FF09F7EEC3B306FD44F1A"
    "BDA99C6EC5EE5DFBB2E451F4ECA350C2"
)

EXPECTED_BLIND_INPUT_SHA256 = (
    "22D3A1C184F95D65D9571191A1FFF01A"
    "D251050C554BA6D96F15FBABBFDF9D6B"
)

EXPECTED_THRESHOLDS_V2_SHA256 = (
    "1BDD2ED8950D6E3E612C66DCD5384BD5"
    "E0CAC784E39A70C3CE09EAD5C310D277"
)

EXPECTED_MODEL = "gpt-5.4-mini"
EXPECTED_REASONING_EFFORT = "none"
EXPECTED_MAX_COMPLETION_TOKENS = 800
EXPECTED_TEMPERATURE = 0.0
EXPECTED_CASE_COUNT = 40

ALLOWED_PREDICTION_STATUSES = {
    "prediction",
    "error",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(
    path: Path,
    expected: str,
    label: str,
) -> None:
    if not path.exists():
        raise SystemExit(
            f"Required file not found: {path}"
        )

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze prediction result v2."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

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

    if SCORE_PATH.exists() or SCORE_RESULT_PATH.exists():
        raise RuntimeError(
            "A score artifact already exists before prediction-result freeze. "
            "Refusing to proceed."
        )

    require_sha(
        PREDICTIONS_PATH,
        EXPECTED_PREDICTION_SHA256,
        "First untouched prediction artifact v2",
    )
    require_sha(
        RUN_AUTHORISATION_PATH,
        EXPECTED_RUN_AUTHORISATION_SHA256,
        "Frozen run authorisation v2",
    )

    predictions = load_json(
        PREDICTIONS_PATH
    )
    run_auth = load_json(
        RUN_AUTHORISATION_PATH
    )

    if predictions.get("schema") != (
        "waypoint-source-boundary-classifier-predictions-v2"
    ):
        raise RuntimeError(
            "Unexpected prediction schema."
        )

    if predictions.get("status") != (
        "FIRST_UNTOUCHED_INDEPENDENT_RUN_COMPLETE"
    ):
        raise RuntimeError(
            "Prediction artifact is not marked as the completed first "
            "untouched independent run."
        )

    if run_auth.get("schema") != (
        "waypoint-source-boundary-classifier-run-authorisation-v2"
    ):
        raise RuntimeError(
            "Unexpected run-authorisation schema."
        )

    if run_auth.get("status") != (
        "AUTHORISE_ONE_FIRST_UNTOUCHED_INDEPENDENT_RUN"
    ):
        raise RuntimeError(
            "Run-authorisation status changed."
        )

    prediction_sources = predictions.get(
        "source_artifacts",
        {},
    )

    expected_prediction_sources = {
        "classifier_implementation_v2_sha256": (
            EXPECTED_CLASSIFIER_SHA256
        ),
        "classifier_prompt_sha256": (
            EXPECTED_PROMPT_SHA256
        ),
        "blind_input_v2_sha256": (
            EXPECTED_BLIND_INPUT_SHA256
        ),
        "acceptance_thresholds_v2_sha256": (
            EXPECTED_THRESHOLDS_V2_SHA256
        ),
        "run_authorisation_v2_sha256": (
            EXPECTED_RUN_AUTHORISATION_SHA256
        ),
    }

    for key, expected in expected_prediction_sources.items():
        actual = prediction_sources.get(key)

        if actual != expected:
            raise RuntimeError(
                f"Prediction source binding changed for {key}.\n"
                f"Expected: {expected}\n"
                f"Actual:   {actual}"
            )

    execution = predictions.get(
        "execution_contract",
        {},
    )

    required_execution = {
        "model": EXPECTED_MODEL,
        "reasoning_effort": EXPECTED_REASONING_EFFORT,
        "max_completion_tokens": (
            EXPECTED_MAX_COMPLETION_TOKENS
        ),
        "temperature": EXPECTED_TEMPERATURE,
        "case_count": EXPECTED_CASE_COUNT,
        "model_call_attempts": EXPECTED_CASE_COUNT,
        "one_model_call_per_case": True,
        "sequential": True,
        "automatic_retry": False,
        "repair_call": False,
        "fallback_model": False,
    }

    for key, expected in required_execution.items():
        actual = execution.get(key)

        if actual != expected:
            raise RuntimeError(
                f"Prediction execution contract changed for {key}.\n"
                f"Expected: {expected!r}\n"
                f"Actual:   {actual!r}"
            )

    results = predictions.get(
        "results",
        {},
    )

    if results.get(
        "completed_predictions"
    ) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            "Expected 40 completed predictions."
        )

    if results.get("errors") != 0:
        raise RuntimeError(
            "This frozen prediction artifact is expected to contain zero "
            "execution/validation errors."
        )

    if results.get(
        "scoring_performed"
    ) is not False:
        raise RuntimeError(
            "Prediction artifact indicates scoring was already performed."
        )

    if results.get(
        "gold_loaded"
    ) is not False:
        raise RuntimeError(
            "Prediction artifact indicates gold was loaded during the run."
        )

    if results.get(
        "threshold_file_loaded"
    ) is not False:
        raise RuntimeError(
            "Prediction artifact indicates the threshold file was loaded "
            "during the blind run."
        )

    cases = predictions.get("cases")

    if (
        not isinstance(cases, list)
        or len(cases) != EXPECTED_CASE_COUNT
    ):
        raise RuntimeError(
            "Prediction artifact must contain exactly 40 cases."
        )

    seen_ids: set[str] = set()
    prediction_count = 0
    error_count = 0

    for index, item in enumerate(
        cases,
        start=1,
    ):
        if not isinstance(item, dict):
            raise RuntimeError(
                f"Prediction case {index} is not an object."
            )

        case_id = item.get("case_id")
        status = item.get("status")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                f"Prediction case {index} has invalid case_id."
            )

        if case_id in seen_ids:
            raise RuntimeError(
                f"Duplicate prediction case_id: {case_id}"
            )

        if status not in ALLOWED_PREDICTION_STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid prediction status {status!r}."
            )

        seen_ids.add(case_id)

        if status == "prediction":
            prediction_count += 1

            required_fields = {
                "resolution_status",
                "source_domain",
                "source_class",
                "responsible_authority_type",
                "basis",
            }

            missing = sorted(
                field
                for field in required_fields
                if field not in item
            )

            if missing:
                raise RuntimeError(
                    f"{case_id}: prediction is missing fields: "
                    + ", ".join(missing)
                )
        else:
            error_count += 1

    if prediction_count != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            f"Expected 40 prediction-status cases; found {prediction_count}."
        )

    if error_count != 0:
        raise RuntimeError(
            f"Expected 0 error-status cases; found {error_count}."
        )

    prediction_auth = predictions.get(
        "authorisations",
        {},
    )

    if prediction_auth.get(
        "prediction_result_freeze_authorised"
    ) is not True:
        raise RuntimeError(
            "Prediction artifact does not authorise result freeze."
        )

    if prediction_auth.get(
        "repeat_run_authorised"
    ) is not False:
        raise RuntimeError(
            "Prediction artifact unexpectedly authorises a repeat run."
        )

    artifact = {
        "schema": (
            "waypoint-source-boundary-classifier-prediction-result-v2"
        ),
        "status": (
            "FROZEN_FIRST_UNTOUCHED_INDEPENDENT_PREDICTION_RESULT"
        ),
        "frozen_on": str(date.today()),
        "prediction_sha256": (
            EXPECTED_PREDICTION_SHA256
        ),
        "source_artifacts": {
            "prediction_sha256": (
                EXPECTED_PREDICTION_SHA256
            ),
            "run_authorisation_v2_sha256": (
                EXPECTED_RUN_AUTHORISATION_SHA256
            ),
            "classifier_implementation_v2_sha256": (
                EXPECTED_CLASSIFIER_SHA256
            ),
            "classifier_prompt_sha256": (
                EXPECTED_PROMPT_SHA256
            ),
            "blind_input_v2_sha256": (
                EXPECTED_BLIND_INPUT_SHA256
            ),
            "acceptance_thresholds_v2_sha256": (
                EXPECTED_THRESHOLDS_V2_SHA256
            ),
        },
        "execution_result": {
            "case_count": EXPECTED_CASE_COUNT,
            "model_call_attempts": EXPECTED_CASE_COUNT,
            "completed_predictions": prediction_count,
            "errors": error_count,
            "model": EXPECTED_MODEL,
            "reasoning_effort": (
                EXPECTED_REASONING_EFFORT
            ),
            "max_completion_tokens": (
                EXPECTED_MAX_COMPLETION_TOKENS
            ),
            "temperature": (
                EXPECTED_TEMPERATURE
            ),
            "one_model_call_per_case": True,
            "sequential": True,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
        },
        "blindness_result": {
            "gold_loaded_during_prediction": False,
            "threshold_file_loaded_during_prediction": False,
            "scoring_performed_during_prediction": False,
        },
        "immutability": {
            "prediction_artifact_frozen": True,
            "prediction_sha256": (
                EXPECTED_PREDICTION_SHA256
            ),
            "repeat_run_authorised": False,
            "prediction_overwrite_authorised": False,
            "threshold_change_before_scoring_authorised": False,
        },
        "methodology": {
            "run_claim": (
                "FIRST_UNTOUCHED_INDEPENDENT_ACCEPTANCE_RUN"
            ),
            "first_run_complete": True,
            "prediction_frozen_before_gold_scoring": True,
            "same_prediction_set_required_for_scoring": True,
            "manual_override": False,
        },
        "authorisations": {
            "scoring_authorised": True,
            "score_result_freeze_authorised_after_scoring": True,
            "repeat_run_authorised": False,
            "prediction_change_authorised": False,
            "threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "score_first_untouched_source_boundary_classifier_run_v2"
            ),
            "authorised": True,
            "command": (
                "uv run python -m "
                "scripts.score_source_boundary_classifier_independent_v2"
            ),
            "purpose": (
                "Score this exact frozen first-run prediction artifact once "
                "against the already-frozen independent pack v5 and "
                "acceptance thresholds v2."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(
        OUTPUT_PATH
    )

    if saved.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_INDEPENDENT_PREDICTION_RESULT"
    ):
        raise RuntimeError(
            "Saved prediction-result status changed."
        )

    if saved.get(
        "prediction_sha256"
    ) != EXPECTED_PREDICTION_SHA256:
        raise RuntimeError(
            "Saved prediction-result SHA binding changed."
        )

    saved_auth = saved.get(
        "authorisations",
        {},
    )

    if saved_auth.get(
        "scoring_authorised"
    ) is not True:
        raise RuntimeError(
            "Prediction-result freeze did not authorise scoring."
        )

    for forbidden in (
        "repeat_run_authorised",
        "prediction_change_authorised",
        "threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Prediction-result freeze unexpectedly enables {forbidden}."
            )

    print("Waypoint source-boundary classifier prediction-result freeze v2")
    print("=" * 72)
    print(
        f"Prediction SHA256:          "
        f"{sha256(PREDICTIONS_PATH)}"
    )
    print(
        f"Run-authorisation SHA256:   "
        f"{sha256(RUN_AUTHORISATION_PATH)}"
    )
    print()
    print("First untouched run")
    print("-" * 72)
    print("Cases:                      40")
    print("Model-call attempts:        40")
    print("Completed predictions:      40")
    print("Errors:                     0")
    print("Automatic retry:            NO")
    print("Repair call:                NO")
    print("Fallback model:             NO")
    print()
    print("Blindness")
    print("-" * 72)
    print("Gold loaded during run:     NO")
    print("Threshold file loaded:      NO")
    print("Scoring already performed:  NO")
    print()
    print("Prediction artifact:        FROZEN")
    print("Repeat run:                 NOT AUTHORISED")
    print("Prediction changes:         NOT AUTHORISED")
    print("Threshold changes:          NOT AUTHORISED")
    print("Scoring:                    AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  SCORE FROZEN FIRST RUN")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(
        f"Prediction-result SHA256:   "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Gold read by freeze:        NO")
    print("Threshold file read:        NO")
    print()
    print("Prediction-result freeze v2: PASS")


if __name__ == "__main__":
    main()
