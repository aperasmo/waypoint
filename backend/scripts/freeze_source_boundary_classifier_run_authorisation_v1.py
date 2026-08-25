"""Freeze one-time authorisation for the first Waypoint source-boundary classifier run.

This script makes NO model calls.

It authorises exactly one first 34-case synthetic contract run, bound to the
already reviewed experimental bundle, frozen contract pack, frozen thresholds,
production runtime, and current configured model settings.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_run_authorisation_v1.py
    uv run python -m scripts.freeze_source_boundary_classifier_run_authorisation_v1

Output:
    tests/source_boundary_classifier_run_authorisation_v1.json

After this artifact is frozen successfully, the separately frozen blind runner
may be executed once.
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

from app.config import get_settings


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

BOUNDARY_PATH = (
    BACKEND_DIR
    / "tests"
    / "authoritative_source_boundary_spec_v1.json"
)

DESIGN_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v2.json"
)

PACK_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v3.json"
)

THRESHOLDS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v1.json"
)

EXPERIMENTAL_DESIGN_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_experimental_design_v1.json"
)

BUNDLE_REVIEW_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_bundle_review_v1.json"
)

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v1.py"
)

RUNNER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "run_source_boundary_classifier_contract_v1.py"
)

SCORER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "score_source_boundary_classifier_contract_v1.py"
)

LEAKAGE_GUARD_PATH = (
    BACKEND_DIR
    / "scripts"
    / "check_source_boundary_classifier_leakage.py"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_run_authorisation_v1.json"
)

PREDICTIONS_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_predictions_v1.json"
)

SCORE_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_v1.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_BOUNDARY_SHA256 = (
    "2BFC518CFD892FE54AD9E46EAEE0037A9"
    "05730DDA934E3EEAEB1EBAD42C1458F"
)

EXPECTED_DESIGN_V2_SHA256 = (
    "2A7D44B8948D66091F5E4F37E5C38284"
    "4C752452E31637AD2199CF0E9232C2F2"
)

EXPECTED_PACK_V3_SHA256 = (
    "C820489715EA3F54138023D680D04DFBF"
    "F5575A515B936FA8C2241E2EA5B219D"
)

EXPECTED_THRESHOLDS_SHA256 = (
    "5E8AFBFFEE5880DEBF4FA6B0A6514E8C"
    "6702F5D9E74D620BA4C1575F49CAC03C"
)

EXPECTED_EXPERIMENTAL_DESIGN_SHA256 = (
    "BC8F47CE6E7C60CC4133C22ACF592CFA"
    "89E9C409C923180017D9C4163A428BDF"
)

EXPECTED_BUNDLE_REVIEW_SHA256 = (
    "70A532977D0AAE2AD227A594D8EAC3542"
    "D970CB25DA894145E7839E818488527"
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

EXPECTED_LEAKAGE_GUARD_SHA256 = (
    "BAF1296A44B5C9E72C0E3C6E78D57EFB"
    "331677B03F9EED2E57BD4E18BA9D598E"
)

EXPECTED_MODEL = "gpt-5.4-mini"
EXPECTED_REASONING_EFFORT = "none"
EXPECTED_MAX_COMPLETION_TOKENS = 800
EXPECTED_CASE_COUNT = 34


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
            "Refusing to freeze classifier run authorisation."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def read_secret_presence(value: Any) -> bool:
    if hasattr(value, "get_secret_value"):
        value = value.get_secret_value()

    return bool(str(value).strip())


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Run-authorisation artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    if PREDICTIONS_PATH.exists():
        raise SystemExit(
            f"Prediction artifact already exists: {PREDICTIONS_PATH}\n"
            "A first-run authorisation cannot be created after predictions "
            "already exist."
        )

    if SCORE_PATH.exists():
        raise SystemExit(
            f"Score artifact already exists: {SCORE_PATH}\n"
            "A first-run authorisation cannot be created after scoring "
            "artifacts already exist."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )
    require_sha(
        BOUNDARY_PATH,
        EXPECTED_BOUNDARY_SHA256,
        "Frozen authoritative-source boundary",
    )
    require_sha(
        DESIGN_V2_PATH,
        EXPECTED_DESIGN_V2_SHA256,
        "Frozen classifier design v2",
    )
    require_sha(
        PACK_V3_PATH,
        EXPECTED_PACK_V3_SHA256,
        "Frozen contract test pack v3",
    )
    require_sha(
        THRESHOLDS_PATH,
        EXPECTED_THRESHOLDS_SHA256,
        "Frozen acceptance thresholds",
    )
    require_sha(
        EXPERIMENTAL_DESIGN_PATH,
        EXPECTED_EXPERIMENTAL_DESIGN_SHA256,
        "Frozen experimental design v1",
    )
    require_sha(
        BUNDLE_REVIEW_PATH,
        EXPECTED_BUNDLE_REVIEW_SHA256,
        "Frozen experimental bundle review v1",
    )
    require_sha(
        CLASSIFIER_PATH,
        EXPECTED_CLASSIFIER_SHA256,
        "Reviewed experimental classifier",
    )
    require_sha(
        RUNNER_PATH,
        EXPECTED_RUNNER_SHA256,
        "Reviewed blind runner",
    )
    require_sha(
        SCORER_PATH,
        EXPECTED_SCORER_SHA256,
        "Reviewed scorer",
    )
    require_sha(
        LEAKAGE_GUARD_PATH,
        EXPECTED_LEAKAGE_GUARD_SHA256,
        "Reviewed leakage guard",
    )

    pack = load_json(PACK_V3_PATH)
    thresholds = load_json(THRESHOLDS_PATH)
    experimental_design = load_json(EXPERIMENTAL_DESIGN_PATH)
    bundle_review = load_json(BUNDLE_REVIEW_PATH)

    if pack.get("schema") != (
        "waypoint-source-boundary-classifier-contract-test-pack-v3"
    ):
        raise RuntimeError(
            "Unexpected contract-test-pack-v3 schema."
        )

    if pack.get("construction", {}).get(
        "test_count"
    ) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            "Contract test-pack case count changed."
        )

    if thresholds.get("schema") != (
        "waypoint-source-boundary-classifier-acceptance-thresholds-v1"
    ):
        raise RuntimeError(
            "Unexpected acceptance-threshold schema."
        )

    if thresholds.get("status") != (
        "FROZEN_BEFORE_FIRST_CLASSIFIER_PREDICTION"
    ):
        raise RuntimeError(
            "Acceptance thresholds are not frozen before prediction."
        )

    if experimental_design.get("schema") != (
        "waypoint-source-boundary-classifier-experimental-design-v1"
    ):
        raise RuntimeError(
            "Unexpected experimental-design schema."
        )

    if experimental_design.get("status") != (
        "FROZEN_DESIGN_ONLY_NO_MODEL_RUN"
    ):
        raise RuntimeError(
            "Experimental design is not frozen."
        )

    if bundle_review.get("schema") != (
        "waypoint-source-boundary-classifier-bundle-review-v1"
    ):
        raise RuntimeError(
            "Unexpected bundle-review schema."
        )

    if bundle_review.get("status") != (
        "APPROVED_READY_FOR_SINGLE_RUN_AUTHORISATION_FREEZE"
    ):
        raise RuntimeError(
            "Bundle review is not approved for run-authorisation freeze."
        )

    review_decision = bundle_review.get(
        "review_decision",
        {},
    )

    if review_decision.get(
        "experimental_bundle_v1"
    ) != "APPROVE":
        raise RuntimeError(
            "Experimental bundle is not approved."
        )

    if review_decision.get(
        "prompt_contract"
    ) != "APPROVE":
        raise RuntimeError(
            "Prompt contract is not approved."
        )

    if review_decision.get(
        "validation_contract"
    ) != "APPROVE":
        raise RuntimeError(
            "Validation contract is not approved."
        )

    if review_decision.get(
        "single_run_authorisation_freeze_authorised"
    ) is not True:
        raise RuntimeError(
            "Bundle review does not authorise this freeze."
        )

    if review_decision.get(
        "classifier_model_prediction_authorised"
    ) is not False:
        raise RuntimeError(
            "Bundle review unexpectedly already authorises prediction."
        )

    bundle = bundle_review.get("bundle")

    if not isinstance(bundle, dict):
        raise RuntimeError(
            "Bundle review is missing frozen bundle metadata."
        )

    expected_bundle_hashes = {
        "classifier": EXPECTED_CLASSIFIER_SHA256,
        "blind_runner": EXPECTED_RUNNER_SHA256,
        "scorer": EXPECTED_SCORER_SHA256,
        "leakage_guard": EXPECTED_LEAKAGE_GUARD_SHA256,
    }

    for component, expected_hash in (
        expected_bundle_hashes.items()
    ):
        component_data = bundle.get(component)

        if not isinstance(component_data, dict):
            raise RuntimeError(
                f"Bundle review is missing {component}."
            )

        if component_data.get("sha256") != expected_hash:
            raise RuntimeError(
                f"Bundle review {component} SHA changed."
            )

    classifier_execution = bundle_review.get(
        "classifier_execution_contract",
        {},
    )

    if classifier_execution.get(
        "reasoning_effort"
    ) != EXPECTED_REASONING_EFFORT:
        raise RuntimeError(
            "Bundle-review reasoning effort changed."
        )

    if classifier_execution.get(
        "max_completion_tokens"
    ) != EXPECTED_MAX_COMPLETION_TOKENS:
        raise RuntimeError(
            "Bundle-review max completion tokens changed."
        )

    if classifier_execution.get(
        "temperature"
    ) != 0:
        raise RuntimeError(
            "Bundle-review temperature changed."
        )

    if classifier_execution.get(
        "model_calls_per_case"
    ) != 1:
        raise RuntimeError(
            "Bundle-review call count per case changed."
        )

    if classifier_execution.get(
        "automatic_retry"
    ) is not False:
        raise RuntimeError(
            "Bundle-review automatic retry changed."
        )

    if classifier_execution.get(
        "repair_call"
    ) is not False:
        raise RuntimeError(
            "Bundle-review repair-call setting changed."
        )

    if classifier_execution.get(
        "fallback_model"
    ) is not False:
        raise RuntimeError(
            "Bundle-review fallback-model setting changed."
        )

    if classifier_execution.get(
        "expected_first_run_cases"
    ) != EXPECTED_CASE_COUNT:
        raise RuntimeError(
            "Bundle-review first-run case count changed."
        )

    settings = get_settings()

    model = str(settings.answer_model).strip()
    reasoning_effort = str(
        settings.answer_reasoning_effort
    ).strip()
    max_tokens = int(settings.answer_max_tokens)

    if model != EXPECTED_MODEL:
        raise SystemExit(
            "Configured answer_model differs from the reviewed execution "
            "contract.\n"
            f"Expected: {EXPECTED_MODEL}\n"
            f"Actual:   {model}\n"
            "Refusing to authorise the run."
        )

    if reasoning_effort != EXPECTED_REASONING_EFFORT:
        raise SystemExit(
            "Configured answer_reasoning_effort differs from the reviewed "
            "execution contract.\n"
            f"Expected: {EXPECTED_REASONING_EFFORT}\n"
            f"Actual:   {reasoning_effort}\n"
            "Refusing to authorise the run."
        )

    if max_tokens != EXPECTED_MAX_COMPLETION_TOKENS:
        raise SystemExit(
            "Configured answer_max_tokens differs from the reviewed "
            "execution contract.\n"
            f"Expected: {EXPECTED_MAX_COMPLETION_TOKENS}\n"
            f"Actual:   {max_tokens}\n"
            "Refusing to authorise the run."
        )

    if not read_secret_presence(settings.openai_api_key):
        raise SystemExit(
            "OpenAI API key is not configured. Refusing to authorise a run "
            "that cannot execute as frozen."
        )

    authorisation = {
        "schema": (
            "waypoint-source-boundary-classifier-run-authorisation-v1"
        ),
        "status": (
            "AUTHORISED_SINGLE_FIRST_CONTRACT_RUN"
        ),
        "authorised_on": str(date.today()),
        "single_run_only": True,
        "purpose": (
            "Authorise exactly one first untouched 34-case synthetic "
            "source-boundary classifier contract run using the reviewed "
            "experimental bundle and frozen acceptance criteria."
        ),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "classifier_design_v2_sha256": EXPECTED_DESIGN_V2_SHA256,
            "contract_test_pack_v3_sha256": EXPECTED_PACK_V3_SHA256,
            "acceptance_thresholds_v1_sha256": (
                EXPECTED_THRESHOLDS_SHA256
            ),
            "experimental_design_v1_sha256": (
                EXPECTED_EXPERIMENTAL_DESIGN_SHA256
            ),
            "bundle_review_v1_sha256": (
                EXPECTED_BUNDLE_REVIEW_SHA256
            ),
            "scorer_sha256": EXPECTED_SCORER_SHA256,
            "leakage_guard_sha256": (
                EXPECTED_LEAKAGE_GUARD_SHA256
            ),
        },
        "frozen_execution": {
            "classifier_sha256": EXPECTED_CLASSIFIER_SHA256,
            "runner_sha256": EXPECTED_RUNNER_SHA256,
            "contract_test_pack_sha256": EXPECTED_PACK_V3_SHA256,
            "acceptance_thresholds_sha256": (
                EXPECTED_THRESHOLDS_SHA256
            ),
            "model": model,
            "reasoning_effort": reasoning_effort,
            "max_completion_tokens": max_tokens,
            "temperature": 0,
            "response_format": "json_object",
            "expected_case_count": EXPECTED_CASE_COUNT,
            "calls_per_case": 1,
            "expected_model_call_attempts": EXPECTED_CASE_COUNT,
            "execution_order": "sequential",
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
        },
        "pre_run_state": {
            "prediction_artifact_absent": True,
            "score_artifact_absent": True,
            "openai_api_key_configured": True,
            "production_runtime_unchanged": True,
            "bundle_review_approved": True,
            "thresholds_frozen_before_prediction": True,
        },
        "allow_retry": False,
        "allow_repair": False,
        "allow_fallback_model": False,
        "allow_pack_changes": False,
        "allow_threshold_changes": False,
        "post_run_rules": [
            (
                "The prediction artifact is immutable and must not be "
                "overwritten."
            ),
            (
                "The same authorisation must not be used to overwrite or "
                "repeat the first-run prediction artifact."
            ),
            (
                "Score the frozen prediction artifact with the separately "
                "reviewed scorer and frozen thresholds."
            ),
            (
                "Do not change thresholds after observing predictions."
            ),
            (
                "If acceptance fails, treat the prediction set as "
                "development evidence rather than lowering thresholds or "
                "claiming the same pack remains untouched."
            ),
            (
                "Passing the synthetic contract pack does not authorise "
                "production integration or establish real-world "
                "generalisation."
            ),
        ],
        "authorisations": {
            "classifier_model_prediction_authorised": True,
            "classifier_contract_run_authorised": True,
            "single_first_run_only": True,
            "scoring_after_prediction_authorised": True,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "run_source_boundary_classifier_contract_v1",
            "authorised": True,
            "command": (
                "uv run python -m "
                "scripts.run_source_boundary_classifier_contract_v1"
            ),
            "expected_model_call_attempts": EXPECTED_CASE_COUNT,
            "automatic_retry": False,
            "after_run": (
                "Freeze the immutable prediction SHA, then run the reviewed "
                "zero-model-call scorer exactly once."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            authorisation,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "AUTHORISED_SINGLE_FIRST_CONTRACT_RUN"
    ):
        raise RuntimeError(
            "Saved authorisation status changed."
        )

    if saved.get("single_run_only") is not True:
        raise RuntimeError(
            "Saved authorisation is not single-run only."
        )

    frozen = saved.get("frozen_execution", {})

    runner_required = {
        "classifier_sha256": EXPECTED_CLASSIFIER_SHA256,
        "runner_sha256": EXPECTED_RUNNER_SHA256,
        "contract_test_pack_sha256": EXPECTED_PACK_V3_SHA256,
        "acceptance_thresholds_sha256": (
            EXPECTED_THRESHOLDS_SHA256
        ),
        "model": EXPECTED_MODEL,
        "reasoning_effort": EXPECTED_REASONING_EFFORT,
        "max_completion_tokens": (
            EXPECTED_MAX_COMPLETION_TOKENS
        ),
        "expected_case_count": EXPECTED_CASE_COUNT,
        "automatic_retry": False,
    }

    for key, expected_value in runner_required.items():
        if frozen.get(key) != expected_value:
            raise RuntimeError(
                "Saved authorisation would fail blind-runner validation "
                f"for {key!r}."
            )

    auth = saved.get("authorisations", {})

    if auth.get(
        "classifier_model_prediction_authorised"
    ) is not True:
        raise RuntimeError(
            "Saved artifact does not authorise classifier prediction."
        )

    if auth.get(
        "classifier_contract_run_authorised"
    ) is not True:
        raise RuntimeError(
            "Saved artifact does not authorise contract run."
        )

    if auth.get(
        "single_first_run_only"
    ) is not True:
        raise RuntimeError(
            "Saved artifact does not restrict execution to first run."
        )

    for forbidden in (
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_source_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Run authorisation unexpectedly enables: {forbidden}"
            )

    print("Waypoint source-boundary classifier single-run authorisation")
    print("=" * 63)
    print(
        f"Production v2 SHA256:       "
        f"{sha256(RUNTIME_PATH)}"
    )
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
        f"Leakage guard SHA256:       "
        f"{sha256(LEAKAGE_GUARD_PATH)}"
    )
    print(
        f"Contract pack SHA256:       "
        f"{sha256(PACK_V3_PATH)}"
    )
    print(
        f"Threshold SHA256:           "
        f"{sha256(THRESHOLDS_PATH)}"
    )
    print(
        f"Bundle-review SHA256:       "
        f"{sha256(BUNDLE_REVIEW_PATH)}"
    )
    print()
    print("Execution contract")
    print("-" * 63)
    print(f"Model:                      {model}")
    print(
        f"Reasoning effort:           "
        f"{reasoning_effort}"
    )
    print(
        f"Max completion tokens:      "
        f"{max_tokens}"
    )
    print("Temperature:                0")
    print("Cases:                      34")
    print("Calls per case:             1")
    print("Expected call attempts:     34")
    print("Execution order:            SEQUENTIAL")
    print("Automatic retry:            NO")
    print("Repair call:                NO")
    print("Fallback model:             NO")
    print()
    print("Pre-run state")
    print("-" * 63)
    print("Prediction artifact:        ABSENT")
    print("Score artifact:             ABSENT")
    print("API key configured:         YES")
    print("Thresholds pre-frozen:      YES")
    print("Bundle review:              APPROVED")
    print()
    print("Classifier model prediction:AUTHORISED")
    print("Contract run:               AUTHORISED")
    print("Single first run only:      YES")
    print("Scoring after run:          AUTHORISED")
    print()
    print("Classifier runtime change:  NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  RUN FIRST CONTRACT PREDICTIONS")
    print(
        "Command:                    uv run python -m "
        "scripts.run_source_boundary_classifier_contract_v1"
    )
    print()
    print(
        f"Output:                     "
        f"{OUTPUT_PATH}"
    )
    print(
        f"Run-authorisation SHA256:   "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls during freeze:  NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Single-run authorisation freeze: PASS")


if __name__ == "__main__":
    main()
