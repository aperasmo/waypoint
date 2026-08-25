"""Blind runner v2 for the Waypoint source-boundary classifier.

EXECUTION COMPONENT, BUT RUN IS GATED.
- Reads ONLY the frozen blind input plus a separate one-run authorisation file.
- Never reads the gold/independent contract pack.
- Never reads acceptance thresholds from disk.
- Never passes case_id to the classifier.
- Exactly one classifier call per case.
- Sequential execution.
- No retry, repair, or fallback.
- Refuses to overwrite predictions.

The model run remains impossible until the separate run-authorisation artifact
exists and explicitly authorises the first untouched run.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _experiments.source_boundary_classifier_v2 import (
    CLASSIFIER_MAX_COMPLETION_TOKENS,
    CLASSIFIER_MODEL,
    CLASSIFIER_REASONING_EFFORT,
    CLASSIFIER_TEMPERATURE,
    classify_source_boundary,
)


BACKEND_DIR = Path(__file__).resolve().parent.parent

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v2.py"
)

BLIND_INPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_blind_input_v2.json"
)

RUN_AUTHORISATION_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_run_authorisation_v2.json"
)

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v2.json"
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

EXPECTED_CASE_COUNT = 40
EXPECTED_MODEL = "gpt-5.4-mini"
EXPECTED_REASONING_EFFORT = "none"
EXPECTED_MAX_COMPLETION_TOKENS = 800
EXPECTED_TEMPERATURE = 0.0

ALLOWED_BLIND_FIELDS = {
    "case_id",
    "unsupported_proposition",
    "trusted_source_context",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be an object.")

    return payload


def require_exact_file(
    path: Path,
    expected_sha: str,
    label: str,
) -> None:
    if not path.exists():
        raise RuntimeError(f"{label} not found: {path}")

    actual = sha256(path)

    if actual != expected_sha:
        raise RuntimeError(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected_sha}\n"
            f"Actual:   {actual}"
        )


def validate_run_authorisation() -> dict[str, Any]:
    if not RUN_AUTHORISATION_PATH.exists():
        raise RuntimeError(
            "Classifier model run is NOT AUTHORISED. "
            "Required run-authorisation artifact is absent."
        )

    auth = load_json(RUN_AUTHORISATION_PATH)

    if auth.get("schema") != (
        "waypoint-source-boundary-classifier-run-authorisation-v2"
    ):
        raise RuntimeError("Unexpected run-authorisation schema.")

    if auth.get("status") != (
        "AUTHORISE_ONE_FIRST_UNTOUCHED_INDEPENDENT_RUN"
    ):
        raise RuntimeError("Run authorisation is not active for the first run.")

    source_artifacts = auth.get("source_artifacts", {})

    expected_sources = {
        "classifier_implementation_v2_sha256": EXPECTED_CLASSIFIER_SHA256,
        "classifier_prompt_sha256": EXPECTED_PROMPT_SHA256,
        "blind_input_v2_sha256": EXPECTED_BLIND_INPUT_SHA256,
        "acceptance_thresholds_v2_sha256": EXPECTED_THRESHOLDS_V2_SHA256,
    }

    for key, expected in expected_sources.items():
        if source_artifacts.get(key) != expected:
            raise RuntimeError(
                f"Run authorisation source binding changed for {key}."
            )

    execution = auth.get("execution_contract", {})

    required_execution = {
        "model": EXPECTED_MODEL,
        "reasoning_effort": EXPECTED_REASONING_EFFORT,
        "max_completion_tokens": EXPECTED_MAX_COMPLETION_TOKENS,
        "temperature": EXPECTED_TEMPERATURE,
        "case_count": EXPECTED_CASE_COUNT,
        "one_model_call_per_case": True,
        "sequential": True,
        "automatic_retry": False,
        "repair_call": False,
        "fallback_model": False,
        "single_first_run_only": True,
    }

    for key, expected in required_execution.items():
        if execution.get(key) != expected:
            raise RuntimeError(
                f"Run authorisation execution contract changed for {key}."
            )

    authorisations = auth.get("authorisations", {})

    if authorisations.get(
        "classifier_model_prediction_authorised"
    ) is not True:
        raise RuntimeError("Classifier model prediction is not authorised.")

    if authorisations.get(
        "first_untouched_independent_run_authorised"
    ) is not True:
        raise RuntimeError("First untouched independent run is not authorised.")

    return auth


async def run() -> None:
    require_exact_file(
        CLASSIFIER_PATH,
        EXPECTED_CLASSIFIER_SHA256,
        "Classifier implementation v2",
    )
    require_exact_file(
        BLIND_INPUT_PATH,
        EXPECTED_BLIND_INPUT_SHA256,
        "Blind input v2",
    )

    if PREDICTIONS_PATH.exists():
        raise RuntimeError(
            f"Predictions already exist: {PREDICTIONS_PATH}\n"
            "Refusing to overwrite or repeat the first untouched run."
        )

    if CLASSIFIER_MODEL != EXPECTED_MODEL:
        raise RuntimeError("Classifier model changed.")
    if CLASSIFIER_REASONING_EFFORT != EXPECTED_REASONING_EFFORT:
        raise RuntimeError("Classifier reasoning effort changed.")
    if (
        CLASSIFIER_MAX_COMPLETION_TOKENS
        != EXPECTED_MAX_COMPLETION_TOKENS
    ):
        raise RuntimeError("Classifier max completion tokens changed.")
    if CLASSIFIER_TEMPERATURE != EXPECTED_TEMPERATURE:
        raise RuntimeError("Classifier temperature changed.")

    auth = validate_run_authorisation()
    blind = load_json(BLIND_INPUT_PATH)

    if blind.get("schema") != (
        "waypoint-source-boundary-classifier-blind-input-v2"
    ):
        raise RuntimeError("Unexpected blind-input schema.")

    if blind.get("status") != (
        "FROZEN_BLIND_INPUT_READY_FOR_EXECUTION_BUNDLE"
    ):
        raise RuntimeError("Blind input is not frozen for execution.")

    cases = blind.get("cases")

    if not isinstance(cases, list) or len(cases) != EXPECTED_CASE_COUNT:
        raise RuntimeError("Blind input must contain exactly 40 cases.")

    seen: set[str] = set()
    results: list[dict[str, Any]] = []
    errors = 0

    print("Waypoint source-boundary classifier blind run v2")
    print("=" * 63)
    print(f"Cases: {len(cases)}")
    print(f"Model: {CLASSIFIER_MODEL}")
    print(f"Reasoning effort: {CLASSIFIER_REASONING_EFFORT}")
    print(
        "Max completion tokens: "
        f"{CLASSIFIER_MAX_COMPLETION_TOKENS}"
    )
    print(f"Classifier SHA: {sha256(CLASSIFIER_PATH)}")
    print(f"Blind-input SHA: {sha256(BLIND_INPUT_PATH)}")
    print("Gold pack loaded: NO")
    print("Expected outputs loaded: NO")
    print("Contrast groups loaded: NO")
    print("Threshold file loaded: NO")
    print("Automatic retry: NO")
    print()

    for index, item in enumerate(cases, start=1):
        if not isinstance(item, dict):
            raise RuntimeError("Blind case must be an object.")

        if set(item) != ALLOWED_BLIND_FIELDS:
            raise RuntimeError(
                f"Blind case {index} contains unauthorised fields."
            )

        case_id = item["case_id"]

        if case_id in seen:
            raise RuntimeError(f"Duplicate blind case_id: {case_id}")

        seen.add(case_id)

        try:
            classification = await classify_source_boundary(
                item["unsupported_proposition"],
                item["trusted_source_context"],
            )

            record = {
                "case_id": case_id,
                "status": "prediction",
                "resolution_status": classification.resolution_status,
                "source_domain": classification.source_domain,
                "source_class": classification.source_class,
                "responsible_authority_type": (
                    classification.responsible_authority_type
                ),
                "basis": classification.basis,
            }

            print(
                f"[{index}/{EXPECTED_CASE_COUNT}] "
                f"{classification.source_class}"
            )
        except Exception as exc:
            errors += 1
            record = {
                "case_id": case_id,
                "status": "error",
                "error_type": type(exc).__name__,
                "error": str(exc),
            }

            print(
                f"[{index}/{EXPECTED_CASE_COUNT}] "
                f"ERROR {type(exc).__name__}"
            )

        results.append(record)

    prediction_count = sum(
        1
        for item in results
        if item["status"] == "prediction"
    )

    artifact = {
        "schema": "waypoint-source-boundary-classifier-predictions-v2",
        "status": "FIRST_UNTOUCHED_INDEPENDENT_RUN_COMPLETE",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_artifacts": {
            "classifier_implementation_v2_sha256": (
                EXPECTED_CLASSIFIER_SHA256
            ),
            "classifier_prompt_sha256": EXPECTED_PROMPT_SHA256,
            "blind_input_v2_sha256": EXPECTED_BLIND_INPUT_SHA256,
            "acceptance_thresholds_v2_sha256": (
                EXPECTED_THRESHOLDS_V2_SHA256
            ),
            "run_authorisation_v2_sha256": (
                sha256(RUN_AUTHORISATION_PATH)
            ),
        },
        "execution_contract": {
            "model": CLASSIFIER_MODEL,
            "reasoning_effort": CLASSIFIER_REASONING_EFFORT,
            "max_completion_tokens": (
                CLASSIFIER_MAX_COMPLETION_TOKENS
            ),
            "temperature": CLASSIFIER_TEMPERATURE,
            "case_count": EXPECTED_CASE_COUNT,
            "model_call_attempts": EXPECTED_CASE_COUNT,
            "one_model_call_per_case": True,
            "sequential": True,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
        },
        "results": {
            "completed_predictions": prediction_count,
            "errors": errors,
            "scoring_performed": False,
            "gold_loaded": False,
            "threshold_file_loaded": False,
        },
        "cases": results,
        "authorisations": {
            "scoring_authorised": False,
            "prediction_result_freeze_authorised": True,
            "repeat_run_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
        },
    }

    PREDICTIONS_PATH.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print()
    print(f"Predictions: {prediction_count}")
    print(f"Errors: {errors}")
    print(f"Prediction artifact: {PREDICTIONS_PATH}")
    print(f"Prediction SHA256: {sha256(PREDICTIONS_PATH)}")
    print("Scoring performed: NO")
    print("Repeat run authorised: NO")
    print("First untouched independent run: COMPLETE")


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
