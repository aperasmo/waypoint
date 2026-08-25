"""Freeze human review approval of Waypoint source-boundary contract test pack v3.

This review verifies that the metadata-only correction resolved the sole
remaining v2 pack blocker and authorises acceptance-threshold freezing.

It does NOT authorise model prediction, classifier implementation, candidate
v7, production changes, or fresh external-v3 evaluation.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_contract_pack_human_review_v3.py
    uv run python -m scripts.freeze_source_boundary_contract_pack_human_review_v3

Output:
    tests/source_boundary_contract_pack_human_review_v3.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


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

PACK_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v2.json"
)

HUMAN_REVIEW_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_contract_pack_human_review_v2.json"
)

PACK_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v3.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_contract_pack_human_review_v3.json"
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

EXPECTED_PACK_V2_SHA256 = (
    "500B6D9E2B3FA7F36C6163CF421D2D2C"
    "676808B696335343EBD85A32A0B70367"
)

EXPECTED_HUMAN_REVIEW_V2_SHA256 = (
    "99AA88D41EB769158A275356C558C77F7"
    "2935A02BA8D49BA21E77BED54B321C6"
)

EXPECTED_PACK_V3_SHA256 = (
    "C820489715EA3F54138023D680D04DFBF"
    "F5575A515B936FA8C2241E2EA5B219D"
)


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
            "Refusing to freeze human review v3."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def index_tests(pack: dict) -> dict[str, dict]:
    tests = pack.get("tests")

    if not isinstance(tests, list):
        raise RuntimeError("Contract test pack tests must be a list.")

    indexed: dict[str, dict] = {}

    for item in tests:
        if not isinstance(item, dict):
            raise RuntimeError("Every contract test must be an object.")

        test_id = item.get("test_id")

        if not isinstance(test_id, str) or not test_id:
            raise RuntimeError("Every contract test requires test_id.")

        if test_id in indexed:
            raise RuntimeError(f"Duplicate test_id: {test_id}")

        indexed[test_id] = item

    return indexed


def canonical(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Human-review v3 artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
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
        PACK_V2_PATH,
        EXPECTED_PACK_V2_SHA256,
        "Frozen contract test pack v2",
    )
    require_sha(
        HUMAN_REVIEW_V2_PATH,
        EXPECTED_HUMAN_REVIEW_V2_SHA256,
        "Frozen human review v2",
    )
    require_sha(
        PACK_V3_PATH,
        EXPECTED_PACK_V3_SHA256,
        "Frozen contract test pack v3",
    )

    design = load_json(DESIGN_V2_PATH)
    pack_v2 = load_json(PACK_V2_PATH)
    review_v2 = load_json(HUMAN_REVIEW_V2_PATH)
    pack_v3 = load_json(PACK_V3_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v2"
    ):
        raise RuntimeError("Unexpected classifier design-v2 schema.")

    if design.get("status") != (
        "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError("Unexpected classifier design-v2 status.")

    if review_v2.get("schema") != (
        "waypoint-source-boundary-contract-pack-human-review-v2"
    ):
        raise RuntimeError("Unexpected human-review-v2 schema.")

    if review_v2.get("review_decision", {}).get(
        "classifier_design_v2"
    ) != "APPROVE":
        raise RuntimeError("Classifier design v2 is not approved.")

    if review_v2.get("review_decision", {}).get(
        "contract_test_pack_v2"
    ) != "REVISE_METADATA_ONLY":
        raise RuntimeError(
            "Human review v2 did not authorise metadata-only replacement."
        )

    if pack_v3.get("schema") != (
        "waypoint-source-boundary-classifier-contract-test-pack-v3"
    ):
        raise RuntimeError("Unexpected contract test-pack-v3 schema.")

    if pack_v3.get("status") != (
        "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError("Unexpected contract test-pack-v3 status.")

    construction = pack_v3.get("construction", {})

    if construction.get("metadata_only_revision") is not True:
        raise RuntimeError("V3 is not marked as metadata-only revision.")

    if construction.get("changed_test_ids") != [
        "sbv2_15",
        "sbv2_16",
    ]:
        raise RuntimeError("Unexpected v3 changed-test list.")

    if construction.get("proposition_texts_changed") is not False:
        raise RuntimeError("V3 reports proposition-text changes.")

    if construction.get("expected_outputs_changed") is not False:
        raise RuntimeError("V3 reports expected-output changes.")

    if construction.get("contrast_groups_changed") is not False:
        raise RuntimeError("V3 reports contrast-group changes.")

    if construction.get("source_taxonomy_changed") is not False:
        raise RuntimeError("V3 reports source-taxonomy changes.")

    if construction.get("test_count") != 34:
        raise RuntimeError("Unexpected v3 test count.")

    if construction.get("resolved_count") != 28:
        raise RuntimeError("Unexpected v3 resolved count.")

    if construction.get("unresolved_count") != 6:
        raise RuntimeError("Unexpected v3 unresolved count.")

    v2_tests = index_tests(pack_v2)
    v3_tests = index_tests(pack_v3)

    if list(v2_tests) != list(v3_tests):
        raise RuntimeError("V3 test IDs/order differ from v2.")

    for test_id in v2_tests:
        before = v2_tests[test_id]
        after = v3_tests[test_id]

        if after.get("unsupported_proposition") != (
            before.get("unsupported_proposition")
        ):
            raise RuntimeError(
                f"{test_id}: proposition changed in v3."
            )

        if canonical(after.get("expected")) != canonical(
            before.get("expected")
        ):
            raise RuntimeError(
                f"{test_id}: expected output changed in v3."
            )

        if after.get("basis") != before.get("basis"):
            raise RuntimeError(
                f"{test_id}: basis changed in v3."
            )

        if after.get("contrast_group") != (
            before.get("contrast_group")
        ):
            raise RuntimeError(
                f"{test_id}: contrast group changed in v3."
            )

        if test_id not in {"sbv2_15", "sbv2_16"}:
            if canonical(after) != canonical(before):
                raise RuntimeError(
                    f"{test_id}: unauthorised v3 test-level change."
                )

    expected_publications = {
        "sbv2_15": "inz_iac",
        "sbv2_16": "inz_advice_to_staff",
    }

    for test_id, publication_family in expected_publications.items():
        before_context = v2_tests[test_id].get(
            "trusted_source_context"
        )
        after_context = v3_tests[test_id].get(
            "trusted_source_context"
        )

        if not isinstance(before_context, dict):
            raise RuntimeError(
                f"{test_id}: v2 source context missing."
            )

        if not isinstance(after_context, dict):
            raise RuntimeError(
                f"{test_id}: v3 source context missing."
            )

        if before_context.get("authority_role") != (
            "immigration_instruction_owner"
        ):
            raise RuntimeError(
                f"{test_id}: v2 reviewed contradiction changed."
            )

        if "authority_role" in after_context:
            raise RuntimeError(
                f"{test_id}: contradictory authority_role remains in v3."
            )

        if after_context.get("publisher_family") != (
            "immigration_new_zealand"
        ):
            raise RuntimeError(
                f"{test_id}: publisher_family changed."
            )

        if after_context.get("publication_family") != (
            publication_family
        ):
            raise RuntimeError(
                f"{test_id}: publication_family changed."
            )

        expected_after = dict(before_context)
        expected_after.pop("authority_role")

        if canonical(after_context) != canonical(expected_after):
            raise RuntimeError(
                f"{test_id}: change exceeds authorised metadata removal."
            )

    # Scoring contract must remain identical to v2.
    if canonical(pack_v3.get("scoring_contract")) != canonical(
        pack_v2.get("scoring_contract")
    ):
        raise RuntimeError(
            "Scoring contract changed between v2 and v3."
        )

    scoring = pack_v3.get("scoring_contract", {})

    if scoring.get("acceptance_thresholds_frozen") is not False:
        raise RuntimeError(
            "Acceptance thresholds unexpectedly frozen in v3 pack."
        )

    if scoring.get("model_prediction_authorised") is not False:
        raise RuntimeError(
            "Model prediction unexpectedly authorised in v3 pack."
        )

    # Confirm every source class and contrast grouping survived.
    if canonical(pack_v3.get("coverage")) != canonical(
        pack_v2.get("coverage")
    ):
        raise RuntimeError(
            "Coverage metadata changed between v2 and v3."
        )

    review = {
        "schema": (
            "waypoint-source-boundary-contract-pack-human-review-v3"
        ),
        "status": "APPROVED_READY_FOR_THRESHOLD_FREEZE",
        "review_date": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "classifier_design_v2_sha256": EXPECTED_DESIGN_V2_SHA256,
            "contract_test_pack_v2_sha256": EXPECTED_PACK_V2_SHA256,
            "human_review_v2_sha256": EXPECTED_HUMAN_REVIEW_V2_SHA256,
            "contract_test_pack_v3_sha256": EXPECTED_PACK_V3_SHA256,
        },
        "review_findings": {
            "classifier_design_v2": "APPROVED_UNCHANGED",
            "contract_test_pack_v3": "APPROVED",
            "metadata_only_revision_verified": True,
            "proposition_texts_preserved": "34/34",
            "expected_outputs_preserved": "34/34",
            "basis_text_preserved": "34/34",
            "contrast_groups_preserved": "34/34",
            "untouched_test_records_preserved": "32/32",
            "scoring_contract_preserved": True,
            "source_class_coverage_preserved": True,
            "resolved_count": 28,
            "unresolved_count": 6,
            "remaining_blocking_findings": 0,
        },
        "review_decision": {
            "classifier_design_v2": "APPROVE",
            "contract_test_pack_v3": "APPROVE",
            "acceptance_threshold_freeze_authorised": True,
            "classifier_model_prediction_authorised": False,
            "classifier_experimental_implementation_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "threshold_freeze_requirements": [
            (
                "Thresholds must be frozen before any classifier model "
                "prediction is generated."
            ),
            (
                "Thresholds must use the already frozen metrics from "
                "classifier design v2 and contract test pack v3."
            ),
            (
                "The primary metric remains four-field exact-match accuracy."
            ),
            (
                "Secondary gates must protect source-domain accuracy, "
                "source-class macro recall, unresolved recall, resolved "
                "recall, contrast-group consistency, and malformed/error "
                "rate."
            ),
            (
                "Per-class recall must be reported even if not every class "
                "receives an independent hard threshold."
            ),
            (
                "No threshold may be changed after the first model prediction "
                "without retiring that prediction set as development data."
            ),
            (
                "Freezing thresholds does not itself authorise classifier "
                "implementation or candidate v7."
            ),
        ],
        "next_engineering_task": {
            "name": "source_boundary_classifier_acceptance_thresholds_v1",
            "authorised": True,
            "model_prediction_authorised": False,
            "runtime_implementation_authorised": False,
            "purpose": (
                "Freeze quantitative acceptance thresholds for the approved "
                "34-case synthetic contract test pack before any classifier "
                "model call."
            ),
        },
        "immutability": {
            "classifier_design_v2_remains_frozen": True,
            "contract_test_pack_v3_remains_frozen": True,
            "human_review_v3_remains_frozen_after_creation": True,
            "do_not_overwrite_prior_artifacts": True,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(review, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "APPROVED_READY_FOR_THRESHOLD_FREEZE"
    ):
        raise RuntimeError(
            "Saved human-review-v3 status changed."
        )

    decision = saved.get("review_decision", {})

    if decision.get(
        "acceptance_threshold_freeze_authorised"
    ) is not True:
        raise RuntimeError(
            "Human review v3 does not authorise threshold freeze."
        )

    for forbidden_authorisation in (
        "classifier_model_prediction_authorised",
        "classifier_experimental_implementation_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_source_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if decision.get(forbidden_authorisation) is not False:
            raise RuntimeError(
                "Human review v3 unexpectedly authorises: "
                f"{forbidden_authorisation}"
            )

    if saved.get("next_engineering_task", {}).get(
        "name"
    ) != "source_boundary_classifier_acceptance_thresholds_v1":
        raise RuntimeError(
            "Unexpected human-review-v3 next engineering task."
        )

    print("Waypoint source-boundary contract-pack human review v3 freeze")
    print("=" * 62)
    print(f"Production v2 SHA256:       {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:       {sha256(BOUNDARY_PATH)}")
    print(f"Classifier design-v2 SHA:   {sha256(DESIGN_V2_PATH)}")
    print(f"Contract test-pack-v3 SHA:  {sha256(PACK_V3_PATH)}")
    print()
    print("Metadata-only correction:   VERIFIED")
    print("Proposition texts:          PRESERVED 34/34")
    print("Expected outputs:           PRESERVED 34/34")
    print("Basis text:                 PRESERVED 34/34")
    print("Contrast groups:            PRESERVED 34/34")
    print("Untouched test records:     PRESERVED 32/32")
    print("Scoring contract:           PRESERVED")
    print("Source-class coverage:      PRESERVED")
    print()
    print("Remaining blockers:         NONE")
    print()
    print("Classifier design v2:       APPROVED")
    print("Contract test pack v3:      APPROVED")
    print()
    print("Threshold freeze:           AUTHORISED")
    print("Classifier model prediction:NOT AUTHORISED")
    print("Classifier implementation:  NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  FREEZE ACCEPTANCE THRESHOLDS")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Human-review-v3 SHA256:     {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Contract-pack human review v3 freeze: PASS")


if __name__ == "__main__":
    main()
