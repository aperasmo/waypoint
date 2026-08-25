"""Freeze the blind input for Waypoint classifier acceptance run v2.

ISOLATION STEP ONLY.
- Reads the approved independent pack v5 once during construction.
- Writes a derived blind artifact containing ONLY:
    case_id
    unsupported_proposition
    trusted_source_context
- Does NOT copy expected outputs, gold basis, or contrast groups.
- Makes no model calls.
- Does not modify the approved pack.

The future blind runner must read this blind artifact, not the gold pack.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_blind_input_v2.py
    uv run python -m scripts.freeze_source_boundary_classifier_blind_input_v2

Output:
    tests/source_boundary_classifier_blind_input_v2.json
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

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v2.py"
)

DESIGN_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
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

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_blind_input_v2.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "8193FCDDB48585EC8A8BA8BCC477D123"
    "011B50F2F38531BEB2D88836975FF949"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
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

ALLOWED_BLIND_CASE_FIELDS = {
    "case_id",
    "unsupported_proposition",
    "trusted_source_context",
}

FORBIDDEN_BLIND_KEYS = {
    "expected",
    "basis",
    "contrast_group",
    "resolution_status",
    "source_domain",
    "source_class",
    "responsible_authority_type",
    "gold",
    "expected_label",
    "expected_output",
    "acceptance_thresholds",
}


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
            "Refusing to freeze blind classifier input."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def scan_keys(value: Any) -> set[str]:
    found: set[str] = set()

    if isinstance(value, dict):
        for key, child in value.items():
            found.add(str(key))
            found.update(scan_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(scan_keys(child))

    return found


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Blind input already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )
    require_sha(
        CLASSIFIER_PATH,
        EXPECTED_CLASSIFIER_SHA256,
        "Approved experimental classifier v2",
    )
    require_sha(
        DESIGN_V3_PATH,
        EXPECTED_DESIGN_V3_SHA256,
        "Frozen classifier design v3",
    )
    require_sha(
        PACK_V5_PATH,
        EXPECTED_PACK_V5_SHA256,
        "Approved independent pack v5",
    )
    require_sha(
        THRESHOLDS_V2_PATH,
        EXPECTED_THRESHOLDS_V2_SHA256,
        "Frozen acceptance thresholds v2",
    )
    require_sha(
        IMPLEMENTATION_REVIEW_PATH,
        EXPECTED_IMPLEMENTATION_REVIEW_SHA256,
        "Approved classifier implementation review v2",
    )

    pack = load_json(PACK_V5_PATH)
    review = load_json(IMPLEMENTATION_REVIEW_PATH)

    if pack.get("schema") != (
        "waypoint-source-boundary-classifier-independent-contract-test-pack-v5"
    ):
        raise RuntimeError("Unexpected pack-v5 schema.")

    if pack.get("status") != (
        "FROZEN_METADATA_CORRECTED_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError("Unexpected pack-v5 status.")

    if review.get("schema") != (
        "waypoint-source-boundary-classifier-implementation-review-v2"
    ):
        raise RuntimeError(
            "Unexpected implementation-review schema."
        )

    if review.get("status") != (
        "APPROVED_STATIC_IMPLEMENTATION_READY_FOR_EXECUTION_BUNDLE_CONSTRUCTION"
    ):
        raise RuntimeError(
            "Implementation review does not authorise execution-bundle construction."
        )

    auth = review.get("authorisations", {})

    if auth.get(
        "blind_runner_v2_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Blind-runner construction is not authorised."
        )

    tests = pack.get("tests")

    if not isinstance(tests, list) or len(tests) != 40:
        raise RuntimeError(
            "Approved pack v5 must contain exactly 40 tests."
        )

    blind_cases: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for item in tests:
        if not isinstance(item, dict):
            raise RuntimeError(
                "Every pack-v5 test must be a JSON object."
            )

        case_id = item.get("case_id")
        proposition = item.get("unsupported_proposition")
        context = item.get("trusted_source_context")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Invalid case_id in pack v5.")

        if case_id in seen_ids:
            raise RuntimeError(
                f"Duplicate case_id in pack v5: {case_id}"
            )

        if not isinstance(proposition, str) or not proposition.strip():
            raise RuntimeError(
                f"{case_id}: unsupported_proposition is invalid."
            )

        if context is not None and not isinstance(context, dict):
            raise RuntimeError(
                f"{case_id}: trusted_source_context must be object or null."
            )

        blind_case = {
            "case_id": case_id,
            "unsupported_proposition": proposition,
            "trusted_source_context": context,
        }

        if set(blind_case) != ALLOWED_BLIND_CASE_FIELDS:
            raise RuntimeError(
                f"{case_id}: blind case field set changed."
            )

        blind_cases.append(blind_case)
        seen_ids.add(case_id)

    if len(blind_cases) != 40:
        raise RuntimeError(
            "Blind input must contain exactly 40 cases."
        )

    artifact = {
        "schema": (
            "waypoint-source-boundary-classifier-blind-input-v2"
        ),
        "status": (
            "FROZEN_BLIND_INPUT_READY_FOR_EXECUTION_BUNDLE"
        ),
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "classifier_implementation_v2_sha256": (
                EXPECTED_CLASSIFIER_SHA256
            ),
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
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
        },
        "blind_contract": {
            "case_count": 40,
            "allowed_case_fields": sorted(
                ALLOWED_BLIND_CASE_FIELDS
            ),
            "gold_fields_present": False,
            "expected_outputs_present": False,
            "basis_present": False,
            "contrast_groups_present": False,
            "thresholds_present": False,
            "model_calls": 0,
        },
        "cases": blind_cases,
        "authorisations": {
            "blind_runner_v2_construction_authorised": True,
            "scorer_v2_construction_authorised": True,
            "leakage_guard_v2_construction_authorised": True,
            "execution_bundle_review_v2_construction_authorised": True,
            "classifier_model_run_authorised": False,
            "prediction_authorisation_freeze_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_execution_bundle_v2"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Construct the blind runner, scorer, leakage guard, and "
                "execution-bundle review pinned to this blind artifact."
            ),
        },
    }

    # Deep leakage check before writing.
    keys = scan_keys(artifact)

    leaked_keys = sorted(
        key
        for key in FORBIDDEN_BLIND_KEYS
        if key in keys
    )

    if leaked_keys:
        raise RuntimeError(
            "Forbidden gold/evaluation keys leaked into blind artifact: "
            + ", ".join(leaked_keys)
        )

    # Case IDs remain correlation handles only. Ensure all cases are present.
    if len({case["case_id"] for case in blind_cases}) != 40:
        raise RuntimeError(
            "Blind input case-ID uniqueness check failed."
        )

    OUTPUT_PATH.write_text(
        json.dumps(
            artifact,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_BLIND_INPUT_READY_FOR_EXECUTION_BUNDLE"
    ):
        raise RuntimeError(
            "Saved blind-input status changed."
        )

    saved_cases = saved.get("cases")

    if not isinstance(saved_cases, list) or len(saved_cases) != 40:
        raise RuntimeError(
            "Saved blind input case count changed."
        )

    for item in saved_cases:
        if set(item) != ALLOWED_BLIND_CASE_FIELDS:
            raise RuntimeError(
                "Saved blind case contains an unauthorised field."
            )

    saved_keys = scan_keys(saved)
    leaked_saved_keys = sorted(
        key
        for key in FORBIDDEN_BLIND_KEYS
        if key in saved_keys
    )

    if leaked_saved_keys:
        raise RuntimeError(
            "Saved blind artifact contains forbidden keys: "
            + ", ".join(leaked_saved_keys)
        )

    saved_auth = saved.get("authorisations", {})

    for required in (
        "blind_runner_v2_construction_authorised",
        "scorer_v2_construction_authorised",
        "leakage_guard_v2_construction_authorised",
        "execution_bundle_review_v2_construction_authorised",
    ):
        if saved_auth.get(required) is not True:
            raise RuntimeError(
                f"Blind input did not authorise {required}."
            )

    for forbidden in (
        "classifier_model_run_authorised",
        "prediction_authorisation_freeze_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Blind input unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier blind input v2 freeze")
    print("=" * 67)
    print(
        f"Classifier SHA256:          "
        f"{sha256(CLASSIFIER_PATH)}"
    )
    print(
        f"Pack-v5 SHA256:             "
        f"{sha256(PACK_V5_PATH)}"
    )
    print(
        f"Threshold-v2 SHA256:        "
        f"{sha256(THRESHOLDS_V2_PATH)}"
    )
    print(
        f"Implementation review SHA:  "
        f"{sha256(IMPLEMENTATION_REVIEW_PATH)}"
    )
    print()
    print("Blind contract")
    print("-" * 67)
    print("Cases:                      40")
    print("case_id:                    INCLUDED")
    print("unsupported_proposition:    INCLUDED")
    print("trusted_source_context:     INCLUDED")
    print("Expected outputs:           EXCLUDED")
    print("Gold basis:                 EXCLUDED")
    print("Contrast groups:            EXCLUDED")
    print("Acceptance thresholds:      EXCLUDED")
    print("Forbidden-key scan:         PASS")
    print()
    print("Blind runner construction:  AUTHORISED")
    print("Scorer construction:        AUTHORISED")
    print("Leakage guard construction: AUTHORISED")
    print("Bundle review construction: AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  EXECUTION BUNDLE V2")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Blind-input SHA256:         {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Blind input v2 freeze: PASS")


if __name__ == "__main__":
    main()
