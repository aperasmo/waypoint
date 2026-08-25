"""Freeze one-time authorisation for the first untouched classifier run v2.

AUTHORISATION ONLY.
- No model calls.
- No predictions.
- No scoring.
- Binds the exact reviewed execution bundle.
- Requires prediction/result/score artifacts to be absent.
- Requires OPENAI_API_KEY to be configured.
- Authorises exactly one first untouched 40-case run.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_run_authorisation_v2.py
    uv run python -m scripts.freeze_source_boundary_classifier_run_authorisation_v2

Output:
    tests/source_boundary_classifier_run_authorisation_v2.json
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v2.py"
)

RUNNER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "run_source_boundary_classifier_blind_v2.py"
)

SCORER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "score_source_boundary_classifier_independent_v2.py"
)

GUARD_PATH = (
    BACKEND_DIR
    / "scripts"
    / "check_source_boundary_classifier_execution_bundle_leakage_v2.py"
)

BLIND_INPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_blind_input_v2.json"
)

PACK_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v5.json"
)

THRESHOLDS_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v2.json"
)

IMPLEMENTATION_REVIEW_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_implementation_review_v2.json"
)

BUNDLE_REVIEW_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_execution_bundle_review_v2.json"
)

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v2.json"
)

PREDICTION_RESULT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_prediction_result_v2.json"
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
    / "source_boundary_classifier_run_authorisation_v2.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "8193FCDDB48585EC8A8BA8BCC477D123"
    "011B50F2F38531BEB2D88836975FF949"
)

EXPECTED_PROMPT_SHA256 = (
    "4A5C725B528FF09F7EEC3B306FD44F1A"
    "BDA99C6EC5EE5DFBB2E451F4ECA350C2"
)

EXPECTED_RUNNER_SHA256 = (
    "4279E0B771DFCB69202D99722292F45A"
    "90BE8FDF454C67B834D52A01E8F46A58"
)

EXPECTED_SCORER_SHA256 = (
    "0871AA74522CDF14EE58F7C0A8D3101C"
    "080FCE7B1BB531A17A3267FD934737E4"
)

EXPECTED_GUARD_SHA256 = (
    "BFFB174554ADA901A56D119481100BB74"
    "80A0E8B32E96CA2A2961D4BC501E3D8"
)

EXPECTED_BLIND_INPUT_SHA256 = (
    "22D3A1C184F95D65D9571191A1FFF01A"
    "D251050C554BA6D96F15FBABBFDF9D6B"
)

EXPECTED_PACK_V5_SHA256 = (
    "1B3CEA56504E3932C7DCA342DF99DC225"
    "23A4676B1C22714B9A122DDD566E67B"
)

EXPECTED_THRESHOLDS_V2_SHA256 = (
    "1BDD2ED8950D6E3E612C66DCD5384BD5"
    "E0CAC784E39A70C3CE09EAD5C310D277"
)

EXPECTED_IMPLEMENTATION_REVIEW_SHA256 = (
    "222C11F1CEEDE217CB9F34B7771E837B"
    "CB2E92065C7D1C4FB42CC0F18A85FA1A"
)

EXPECTED_BUNDLE_REVIEW_SHA256 = (
    "9563301C445837BC11035E1EF9B361263"
    "C0DE839A1B3B1985E17FF82558B5986"
)

EXPECTED_MODEL = "gpt-5.4-mini"
EXPECTED_REASONING_EFFORT = "none"
EXPECTED_MAX_COMPLETION_TOKENS = 800
EXPECTED_TEMPERATURE = 0.0
EXPECTED_CASE_COUNT = 40


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
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze run authorisation v2."
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
            f"Run-authorisation artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    for path, expected, label in (
        (
            RUNTIME_PATH,
            EXPECTED_RUNTIME_SHA256,
            "Frozen production candidate-v2 runtime",
        ),
        (
            CLASSIFIER_PATH,
            EXPECTED_CLASSIFIER_SHA256,
            "Approved classifier implementation v2",
        ),
        (
            RUNNER_PATH,
            EXPECTED_RUNNER_SHA256,
            "Approved blind runner v2",
        ),
        (
            SCORER_PATH,
            EXPECTED_SCORER_SHA256,
            "Approved scorer v2",
        ),
        (
            GUARD_PATH,
            EXPECTED_GUARD_SHA256,
            "Approved leakage guard v2",
        ),
        (
            BLIND_INPUT_PATH,
            EXPECTED_BLIND_INPUT_SHA256,
            "Frozen blind input v2",
        ),
        (
            PACK_V5_PATH,
            EXPECTED_PACK_V5_SHA256,
            "Approved independent pack v5",
        ),
        (
            THRESHOLDS_V2_PATH,
            EXPECTED_THRESHOLDS_V2_SHA256,
            "Frozen acceptance thresholds v2",
        ),
        (
            IMPLEMENTATION_REVIEW_PATH,
            EXPECTED_IMPLEMENTATION_REVIEW_SHA256,
            "Approved implementation review v2",
        ),
        (
            BUNDLE_REVIEW_PATH,
            EXPECTED_BUNDLE_REVIEW_SHA256,
            "Approved execution-bundle review v2",
        ),
    ):
        require_sha(path, expected, label)

    implementation_review = load_json(
        IMPLEMENTATION_REVIEW_PATH
    )
    bundle_review = load_json(
        BUNDLE_REVIEW_PATH
    )
    blind_input = load_json(
        BLIND_INPUT_PATH
    )
    thresholds = load_json(
        THRESHOLDS_V2_PATH
    )

    if implementation_review.get("status") != (
        "APPROVED_STATIC_IMPLEMENTATION_READY_FOR_EXECUTION_BUNDLE_CONSTRUCTION"
    ):
        raise RuntimeError(
            "Implementation review status changed."
        )

    if bundle_review.get("schema") != (
        "waypoint-source-boundary-classifier-execution-bundle-review-v2"
    ):
        raise RuntimeError(
            "Unexpected bundle-review schema."
        )

    if bundle_review.get("status") != (
        "APPROVED_READY_FOR_SINGLE_RUN_AUTHORISATION_FREEZE"
    ):
        raise RuntimeError(
            "Execution bundle is not approved for run-authorisation freeze."
        )

    if bundle_review.get(
        "authorisations",
        {},
    ).get(
        "single_run_authorisation_freeze_authorised"
    ) is not True:
        raise RuntimeError(
            "Single-run authorisation freeze is not authorised."
        )

    if bundle_review.get(
        "authorisations",
        {},
    ).get(
        "classifier_model_run_authorised"
    ) is not False:
        raise RuntimeError(
            "Bundle review unexpectedly already authorises model execution."
        )

    if blind_input.get("schema") != (
        "waypoint-source-boundary-classifier-blind-input-v2"
    ):
        raise RuntimeError(
            "Unexpected blind-input schema."
        )

    if blind_input.get("status") != (
        "FROZEN_BLIND_INPUT_READY_FOR_EXECUTION_BUNDLE"
    ):
        raise RuntimeError(
            "Blind input is not frozen for execution."
        )

    blind_cases = blind_input.get("cases")

    if (
        not isinstance(blind_cases, list)
        or len(blind_cases) != EXPECTED_CASE_COUNT
    ):
        raise RuntimeError(
            "Blind input must contain exactly 40 cases."
        )

    if thresholds.get("schema") != (
        "waypoint-source-boundary-classifier-acceptance-thresholds-v2"
    ):
        raise RuntimeError(
            "Unexpected thresholds-v2 schema."
        )

    if thresholds.get("status") != (
        "FROZEN_BEFORE_CLASSIFIER_IMPLEMENTATION_AND_PREDICTION"
    ):
        raise RuntimeError(
            "Acceptance thresholds are not frozen before prediction."
        )

    # First-run freshness gate.
    forbidden_existing = [
        PREDICTIONS_PATH,
        PREDICTION_RESULT_PATH,
        SCORE_PATH,
        SCORE_RESULT_PATH,
    ]

    existing = [
        str(path)
        for path in forbidden_existing
        if path.exists()
    ]

    if existing:
        raise RuntimeError(
            "First untouched run cannot be authorised because result "
            "artifacts already exist:\n"
            + "\n".join(existing)
        )

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured in this process environment."
        )

    # Never print or persist the key itself.
    if len(api_key) < 10:
        raise RuntimeError(
            "OPENAI_API_KEY appears malformed or unexpectedly short."
        )

    artifact = {
        "schema": (
            "waypoint-source-boundary-classifier-run-authorisation-v2"
        ),
        "status": (
            "AUTHORISE_ONE_FIRST_UNTOUCHED_INDEPENDENT_RUN"
        ),
        "authorised_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "classifier_implementation_v2_sha256": (
                EXPECTED_CLASSIFIER_SHA256
            ),
            "classifier_prompt_sha256": (
                EXPECTED_PROMPT_SHA256
            ),
            "blind_runner_v2_sha256": (
                EXPECTED_RUNNER_SHA256
            ),
            "scorer_v2_sha256": (
                EXPECTED_SCORER_SHA256
            ),
            "leakage_guard_v2_sha256": (
                EXPECTED_GUARD_SHA256
            ),
            "blind_input_v2_sha256": (
                EXPECTED_BLIND_INPUT_SHA256
            ),
            "independent_contract_pack_v5_sha256": (
                EXPECTED_PACK_V5_SHA256
            ),
            "acceptance_thresholds_v2_sha256": (
                EXPECTED_THRESHOLDS_V2_SHA256
            ),
            "implementation_review_v2_sha256": (
                EXPECTED_IMPLEMENTATION_REVIEW_SHA256
            ),
            "execution_bundle_review_v2_sha256": (
                EXPECTED_BUNDLE_REVIEW_SHA256
            ),
        },
        "execution_contract": {
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
            "case_count": (
                EXPECTED_CASE_COUNT
            ),
            "one_model_call_per_case": True,
            "sequential": True,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "single_first_run_only": True,
        },
        "freshness_checks": {
            "predictions_v2_absent": True,
            "prediction_result_v2_absent": True,
            "score_v2_absent": True,
            "score_result_v2_absent": True,
            "api_key_configured": True,
            "api_key_persisted_in_artifact": False,
        },
        "blindness_contract": {
            "runner_reads_gold_pack": False,
            "runner_reads_threshold_file": False,
            "case_id_passed_to_model": False,
            "model_receives": [
                "unsupported_proposition",
                "trusted_source_context",
            ],
        },
        "methodology": {
            "first_run_claim": (
                "FIRST_UNTOUCHED_INDEPENDENT_ACCEPTANCE_RUN"
            ),
            "thresholds_frozen_before_prediction": True,
            "independent_pack_frozen_before_prediction": True,
            "classifier_frozen_before_prediction": True,
            "runner_frozen_before_prediction": True,
            "no_manual_override": True,
            "no_retry": True,
            "prediction_must_be_frozen_before_scoring": True,
        },
        "authorisations": {
            "classifier_model_prediction_authorised": True,
            "first_untouched_independent_run_authorised": True,
            "prediction_result_freeze_authorised_after_run": True,
            "scoring_authorised": False,
            "repeat_run_authorised": False,
            "threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "first_untouched_source_boundary_classifier_run_v2"
            ),
            "authorised": True,
            "command": (
                "uv run python -m "
                "scripts.run_source_boundary_classifier_blind_v2"
            ),
            "purpose": (
                "Execute exactly one sequential 40-case blind model run "
                "against the frozen independent acceptance input."
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
        "AUTHORISE_ONE_FIRST_UNTOUCHED_INDEPENDENT_RUN"
    ):
        raise RuntimeError(
            "Saved run-authorisation status changed."
        )

    saved_auth = saved.get(
        "authorisations",
        {},
    )

    if saved_auth.get(
        "classifier_model_prediction_authorised"
    ) is not True:
        raise RuntimeError(
            "Model prediction was not authorised."
        )

    if saved_auth.get(
        "first_untouched_independent_run_authorised"
    ) is not True:
        raise RuntimeError(
            "First untouched run was not authorised."
        )

    for forbidden in (
        "scoring_authorised",
        "repeat_run_authorised",
        "threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Run authorisation unexpectedly enables {forbidden}."
            )

    print("Waypoint source-boundary classifier run authorisation v2")
    print("=" * 68)
    print(
        f"Classifier SHA256:          "
        f"{sha256(CLASSIFIER_PATH)}"
    )
    print(
        f"Runner SHA256:              "
        f"{sha256(RUNNER_PATH)}"
    )
    print(
        f"Scorer SHA256:              "
        f"{sha256(SCORER_PATH)}"
    )
    print(
        f"Guard SHA256:               "
        f"{sha256(GUARD_PATH)}"
    )
    print(
        f"Blind-input SHA256:         "
        f"{sha256(BLIND_INPUT_PATH)}"
    )
    print(
        f"Threshold-v2 SHA256:        "
        f"{sha256(THRESHOLDS_V2_PATH)}"
    )
    print(
        f"Bundle-review SHA256:       "
        f"{sha256(BUNDLE_REVIEW_PATH)}"
    )
    print()
    print("Execution contract")
    print("-" * 68)
    print("Model:                      gpt-5.4-mini")
    print("Reasoning effort:           none")
    print("Max completion tokens:      800")
    print("Temperature:                0")
    print("Cases:                      40")
    print("One call per case:          YES")
    print("Sequential:                 YES")
    print("Automatic retry:            NO")
    print("Repair call:                NO")
    print("Fallback model:             NO")
    print()
    print("Freshness")
    print("-" * 68)
    print("Predictions v2 present:     NO")
    print("Prediction result present:  NO")
    print("Score v2 present:           NO")
    print("Score result present:       NO")
    print("API key configured:         YES")
    print()
    print("Blindness")
    print("-" * 68)
    print("Runner reads gold pack:     NO")
    print("Runner reads thresholds:    NO")
    print("case_id passed to model:    NO")
    print()
    print("Classifier model run:       AUTHORISED")
    print("First untouched run:        AUTHORISED")
    print("Single first run only:      YES")
    print("Scoring:                    NOT AUTHORISED")
    print("Repeat run:                 NOT AUTHORISED")
    print("Threshold changes:          NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print(
        "Next task:                  "
        "FIRST UNTOUCHED 40-CASE RUN"
    )
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(
        f"Run-authorisation SHA256:   "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Run authorisation v2 freeze: PASS")


if __name__ == "__main__":
    main()
