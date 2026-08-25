"""Blind runner for the Waypoint experimental source-boundary classifier.

EXPERIMENTAL ONLY.

This runner:
- reads the approved synthetic contract pack only to extract:
  test_id, unsupported_proposition, trusted_source_context;
- never passes test_id, expected output, basis, contrast group, coverage
  metadata, or thresholds to the classifier;
- executes sequentially;
- makes at most one classifier call per case;
- performs no retry, repair, or fallback;
- refuses to execute unless a separate frozen run-authorisation artifact
  explicitly authorises this exact classifier and runner SHA.

Code build and syntax checking do NOT require run authorisation.

Intended execution command, only after a separate run-authorisation freeze:
    uv run python -m scripts.run_source_boundary_classifier_contract_v1
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from app.config import get_settings
from _experiments.source_boundary_classifier_v1 import (
    CLASSIFIER_MAX_COMPLETION_TOKENS,
    CLASSIFIER_REASONING_EFFORT,
    ClassifierContractError,
    classify_source_boundary,
)


BACKEND_DIR = Path(__file__).resolve().parent.parent

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

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v1.py"
)

AUTHORISATION_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_run_authorisation_v1.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v1.json"
)

EXPECTED_PACK_SHA256 = (
    "C820489715EA3F54138023D680D04DFBF"
    "F5575A515B936FA8C2241E2EA5B219D"
)

EXPECTED_THRESHOLDS_SHA256 = (
    "5E8AFBFFEE5880DEBF4FA6B0A6514E8C"
    "6702F5D9E74D620BA4C1575F49CAC03C"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "BC77C28033F74E3092C8428DE623293D"
    "266FBDEE7FFC237EE79C8AB6F79DE9F3"
)

EXPECTED_PACK_SCHEMA = (
    "waypoint-source-boundary-classifier-contract-test-pack-v3"
)

EXPECTED_AUTHORISATION_SCHEMA = (
    "waypoint-source-boundary-classifier-run-authorisation-v1"
)

EXPECTED_AUTHORISATION_STATUS = (
    "AUTHORISED_SINGLE_FIRST_CONTRACT_RUN"
)

EXPECTED_CASE_COUNT = 34


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


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
            "Refusing to run classifier predictions."
        )


def _extract_api_key(settings: Any) -> str:
    value = settings.openai_api_key

    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()

    api_key = str(value).strip()

    if not api_key:
        raise RuntimeError("Configured OpenAI API key is blank.")

    return api_key


def validate_and_extract_blind_cases(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    if payload.get("schema") != EXPECTED_PACK_SCHEMA:
        raise RuntimeError(
            f"Unexpected contract-pack schema: {payload.get('schema')!r}"
        )

    if payload.get("status") != (
        "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            f"Unexpected contract-pack status: {payload.get('status')!r}"
        )

    construction = payload.get("construction")

    if not isinstance(construction, dict):
        raise RuntimeError("Contract pack is missing construction metadata.")

    if construction.get("test_count") != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            "Contract-pack declared test count is not 34."
        )

    tests = payload.get("tests")

    if not isinstance(tests, list):
        raise RuntimeError("Contract-pack tests must be a list.")

    if len(tests) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CASE_COUNT} tests; got {len(tests)}."
        )

    blind_cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for position, case in enumerate(tests, start=1):
        if not isinstance(case, dict):
            raise RuntimeError(
                f"Contract test {position} must be an object."
            )

        test_id = case.get("test_id")
        proposition = case.get("unsupported_proposition")
        context = case.get("trusted_source_context")

        if not isinstance(test_id, str) or not test_id:
            raise RuntimeError(
                f"Contract test {position} has invalid test_id."
            )

        if test_id in seen_ids:
            raise RuntimeError(f"Duplicate test_id: {test_id}")

        if not isinstance(proposition, str) or not proposition.strip():
            raise RuntimeError(
                f"{test_id}: unsupported_proposition is invalid."
            )

        if context is not None and not isinstance(context, dict):
            raise RuntimeError(
                f"{test_id}: trusted_source_context must be object or null."
            )

        # Deliberately extract only the three fields authorised by the frozen
        # blind-runner contract. No other test-pack fields are copied.
        blind_cases.append(
            {
                "test_id": test_id,
                "unsupported_proposition": proposition.strip(),
                "trusted_source_context": context,
            }
        )

        seen_ids.add(test_id)

    return blind_cases


def validate_run_authorisation(
    payload: dict[str, Any],
    *,
    runner_sha256: str,
    model: str,
) -> None:
    if payload.get("schema") != EXPECTED_AUTHORISATION_SCHEMA:
        raise SystemExit(
            "Classifier run authorisation has unexpected schema."
        )

    if payload.get("status") != EXPECTED_AUTHORISATION_STATUS:
        raise SystemExit(
            "Classifier run is not explicitly authorised."
        )

    if payload.get("single_run_only") is not True:
        raise SystemExit(
            "Run authorisation must explicitly be single-run only."
        )

    expected = {
        "classifier_sha256": EXPECTED_CLASSIFIER_SHA256,
        "runner_sha256": runner_sha256,
        "contract_test_pack_sha256": EXPECTED_PACK_SHA256,
        "acceptance_thresholds_sha256": EXPECTED_THRESHOLDS_SHA256,
        "model": model,
        "reasoning_effort": CLASSIFIER_REASONING_EFFORT,
        "max_completion_tokens": CLASSIFIER_MAX_COMPLETION_TOKENS,
        "expected_case_count": EXPECTED_CASE_COUNT,
        "automatic_retry": False,
    }

    frozen = payload.get("frozen_execution")

    if not isinstance(frozen, dict):
        raise SystemExit(
            "Run authorisation is missing frozen_execution."
        )

    for key, expected_value in expected.items():
        if frozen.get(key) != expected_value:
            raise SystemExit(
                "Run authorisation does not match the frozen execution "
                f"contract for {key!r}.\n"
                f"Expected: {expected_value!r}\n"
                f"Found:    {frozen.get(key)!r}"
            )

    forbidden_truthy = (
        "allow_retry",
        "allow_repair",
        "allow_fallback_model",
        "allow_pack_changes",
        "allow_threshold_changes",
    )

    for key in forbidden_truthy:
        if payload.get(key) not in {False, None}:
            raise SystemExit(
                f"Run authorisation unexpectedly enables {key}."
            )


async def main() -> None:
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
        CLASSIFIER_PATH,
        EXPECTED_CLASSIFIER_SHA256,
        "Frozen experimental classifier",
    )

    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Prediction output already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite the first-run prediction artifact."
        )

    settings = get_settings()

    model = str(settings.answer_model).strip()

    if not model:
        raise SystemExit("Configured answer_model is blank.")

    if str(settings.answer_reasoning_effort) != (
        CLASSIFIER_REASONING_EFFORT
    ):
        raise SystemExit(
            "Configured answer_reasoning_effort differs from the frozen "
            "classifier execution setting."
        )

    if int(settings.answer_max_tokens) != (
        CLASSIFIER_MAX_COMPLETION_TOKENS
    ):
        raise SystemExit(
            "Configured answer_max_tokens differs from the frozen "
            "classifier execution setting."
        )

    # The classifier module deliberately has no dependency on app.config.
    # Make the already-configured project API key available to the OpenAI
    # client without passing it as classifier input or recording it.
    os.environ["OPENAI_API_KEY"] = _extract_api_key(settings)

    pack = load_json(PACK_PATH)
    cases = validate_and_extract_blind_cases(pack)

    runner_path = Path(__file__).resolve()
    runner_sha = sha256(runner_path)

    # This file is intentionally absent until the later explicit
    # run-authorisation freeze. Therefore accidental execution now stops here
    # before any classifier/model call.
    if not AUTHORISATION_PATH.exists():
        raise SystemExit(
            "Classifier contract run is NOT AUTHORISED.\n"
            f"Required authorisation artifact is absent:\n"
            f"{AUTHORISATION_PATH}\n"
            "No model calls were made."
        )

    authorisation = load_json(AUTHORISATION_PATH)
    validate_run_authorisation(
        authorisation,
        runner_sha256=runner_sha,
        model=model,
    )

    predictions: list[dict[str, Any]] = []
    model_call_attempts = 0
    completed_predictions = 0
    errors = 0

    print("Waypoint blind source-boundary classifier contract run")
    print("=" * 56)
    print(f"Cases:                      {len(cases)}")
    print(f"Model:                      {model}")
    print(
        f"Reasoning effort:           "
        f"{CLASSIFIER_REASONING_EFFORT}"
    )
    print(
        f"Max completion tokens:      "
        f"{CLASSIFIER_MAX_COMPLETION_TOKENS}"
    )
    print(f"Classifier SHA256:          {sha256(CLASSIFIER_PATH)}")
    print(f"Runner SHA256:              {runner_sha}")
    print(f"Contract pack SHA256:       {sha256(PACK_PATH)}")
    print(f"Threshold SHA256:           {sha256(THRESHOLDS_PATH)}")
    print(f"Authorisation SHA256:       {sha256(AUTHORISATION_PATH)}")
    print()
    print("Expected outputs loaded:    NO")
    print("Contrast groups loaded:     NO")
    print("Thresholds passed to model: NO")
    print("Retrieval calls:            NONE")
    print("Database writes:            NONE")
    print("Automatic retry:            NO")
    print()
    print("Running first frozen contract predictions...")

    for number, case in enumerate(cases, start=1):
        model_call_attempts += 1

        try:
            result = await classify_source_boundary(
                unsupported_proposition=case["unsupported_proposition"],
                trusted_source_context=case["trusted_source_context"],
                model=model,
            )

            predictions.append(
                {
                    "test_id": case["test_id"],
                    "status": "prediction",
                    "prediction": result.model_dump(mode="json"),
                }
            )

            completed_predictions += 1
            display = result.source_class

        except ClassifierContractError as exc:
            predictions.append(
                {
                    "test_id": case["test_id"],
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

            errors += 1
            display = "ERROR"

        except Exception as exc:
            # Unexpected exceptions are still recorded as acceptance failures.
            # There is no retry or repair.
            predictions.append(
                {
                    "test_id": case["test_id"],
                    "status": "error",
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                }
            )

            errors += 1
            display = "ERROR"

        print(
            f"[{number:>2}/{len(cases)}] "
            f"{case['test_id']}: {display}"
        )

    if model_call_attempts != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            "Unexpected model-call attempt count before output freeze."
        )

    if len(predictions) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            "Unexpected prediction-record count before output freeze."
        )

    output = {
        "schema": "waypoint-source-boundary-classifier-predictions-v1",
        "status": "FIRST_UNTOUCHED_SYNTHETIC_CONTRACT_RUN",
        "source_artifacts": {
            "classifier_sha256": sha256(CLASSIFIER_PATH),
            "runner_sha256": runner_sha,
            "contract_test_pack_sha256": sha256(PACK_PATH),
            "acceptance_thresholds_sha256": sha256(THRESHOLDS_PATH),
            "run_authorisation_sha256": sha256(AUTHORISATION_PATH),
        },
        "model_configuration": {
            "model": model,
            "reasoning_effort": CLASSIFIER_REASONING_EFFORT,
            "max_completion_tokens": CLASSIFIER_MAX_COMPLETION_TOKENS,
            "temperature": 0,
            "response_format": "json_object",
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
        },
        "counts": {
            "case_count": len(cases),
            "model_call_attempts": model_call_attempts,
            "completed_predictions": completed_predictions,
            "errors": errors,
        },
        "predictions": predictions,
    }

    serialised = json.dumps(
        output,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    # Prediction artifacts may contain correlation test IDs, but must not
    # contain gold/expected fields or scoring metadata.
    forbidden_output_fields = (
        '"expected"',
        '"expected_output"',
        '"expected_sections"',
        '"gold"',
        '"contrast_group"',
        '"acceptance_logic"',
        '"hard_gates"',
    )

    lowered = serialised.casefold()
    leaked = [
        token
        for token in forbidden_output_fields
        if token.casefold() in lowered
    ]

    if leaked:
        raise RuntimeError(
            "Prediction artifact contains forbidden scoring/gold fields: "
            + ", ".join(leaked)
        )

    OUTPUT_PATH.write_text(
        serialised,
        encoding="utf-8",
    )

    print()
    print(f"Prediction output:          {OUTPUT_PATH}")
    print(f"Prediction SHA256:          {sha256(OUTPUT_PATH)}")
    print(f"Model-call attempts:        {model_call_attempts}")
    print(f"Completed predictions:      {completed_predictions}")
    print(f"Errors:                     {errors}")
    print()
    print("First frozen contract run:  COMPLETE")
    print("Scoring performed:          NO")


if __name__ == "__main__":
    asyncio.run(main())
