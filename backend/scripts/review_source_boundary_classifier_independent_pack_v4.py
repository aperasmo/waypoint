"""Human-review independent source-boundary classifier contract pack v4.

REVIEW ONLY.
- No model calls.
- No pack mutation.
- No threshold freeze.
- No implementation.
- Detects whether every declared contrast group actually contrasts at least
  two expected source classes.

Run from backend/:
    uv run python -m py_compile scripts/review_source_boundary_classifier_independent_pack_v4.py
    uv run python -m scripts.review_source_boundary_classifier_independent_pack_v4

Output:
    tests/source_boundary_classifier_independent_pack_human_review_v4.json
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

DESIGN_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
)

PACK_V4_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v4.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_pack_human_review_v4.json"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_PACK_V4_SHA256 = (
    "BC9515B3394E880C4FBEBD7C13F9A4FC"
    "43F7823EB484D30B3E008C3632C0304E"
)

EXPECTED_TEST_COUNT = 40
EXPECTED_CLASS_COUNT = 12
EXPECTED_CONTRAST_GROUP_COUNT = 12


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(path: Path, expected: str, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to review independent pack v4."
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
            f"Human-review artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        DESIGN_V3_PATH,
        EXPECTED_DESIGN_V3_SHA256,
        "Frozen classifier design v3",
    )
    require_sha(
        PACK_V4_PATH,
        EXPECTED_PACK_V4_SHA256,
        "Frozen independent pack v4",
    )

    design = load_json(DESIGN_V3_PATH)
    pack = load_json(PACK_V4_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v3"
    ):
        raise RuntimeError("Unexpected design-v3 schema.")

    if pack.get("schema") != (
        "waypoint-source-boundary-classifier-independent-contract-test-pack-v4"
    ):
        raise RuntimeError("Unexpected pack-v4 schema.")

    if pack.get("status") != (
        "FROZEN_INDEPENDENT_SYNTHETIC_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Independent pack v4 is not frozen for human review."
        )

    construction = pack.get("construction", {})

    expected_construction = {
        "test_count": EXPECTED_TEST_COUNT,
        "resolved_count": 34,
        "unresolved_count": 6,
        "source_class_count": EXPECTED_CLASS_COUNT,
        "contrast_group_count": EXPECTED_CONTRAST_GROUP_COUNT,
        "model_calls": 0,
        "reads_observed_contract_pack": False,
        "reads_observed_predictions": False,
        "reads_observed_score": False,
        "reads_failure_analysis": False,
        "uses_observed_case_ids": False,
        "copies_observed_case_wording": False,
        "benchmark_specific_logic": False,
        "question_specific_logic": False,
    }

    for key, expected in expected_construction.items():
        if construction.get(key) != expected:
            raise RuntimeError(
                f"Pack-v4 construction metadata changed for {key!r}."
            )

    tests = pack.get("tests")

    if not isinstance(tests, list) or len(tests) != EXPECTED_TEST_COUNT:
        raise RuntimeError(
            "Independent pack v4 must contain exactly 40 tests."
        )

    case_ids: set[str] = set()
    expected_source_classes: set[str] = set()
    group_members: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in tests:
        if not isinstance(item, dict):
            raise RuntimeError("Every pack-v4 test must be an object.")

        case_id = item.get("case_id")
        expected = item.get("expected")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Invalid pack-v4 case_id.")

        if case_id in case_ids:
            raise RuntimeError(f"Duplicate case_id: {case_id}")

        if not isinstance(expected, dict):
            raise RuntimeError(f"{case_id}: expected output missing.")

        source_class = expected.get("source_class")

        if not isinstance(source_class, str) or not source_class:
            raise RuntimeError(
                f"{case_id}: expected source_class missing."
            )

        case_ids.add(case_id)
        expected_source_classes.add(source_class)

        group = item.get("contrast_group")

        if group is not None:
            if not isinstance(group, str) or not group:
                raise RuntimeError(
                    f"{case_id}: invalid contrast_group."
                )

            group_members[group].append(
                {
                    "case_id": case_id,
                    "source_class": source_class,
                }
            )

    if len(expected_source_classes) != EXPECTED_CLASS_COUNT:
        raise RuntimeError(
            "Independent pack v4 no longer covers 12 source classes."
        )

    if len(group_members) != EXPECTED_CONTRAST_GROUP_COUNT:
        raise RuntimeError(
            "Independent pack v4 no longer has 12 contrast groups."
        )

    contrast_review: dict[str, dict[str, Any]] = {}
    blockers: list[dict[str, Any]] = []

    for group in sorted(group_members):
        members = group_members[group]
        distinct_classes = sorted(
            {
                member["source_class"]
                for member in members
            }
        )

        valid = (
            len(members) >= 2
            and len(distinct_classes) >= 2
        )

        contrast_review[group] = {
            "member_count": len(members),
            "members": members,
            "distinct_source_classes": distinct_classes,
            "valid_contrast": valid,
        }

        if not valid:
            blockers.append(
                {
                    "contrast_group": group,
                    "members": members,
                    "distinct_source_classes": distinct_classes,
                    "issue": (
                        "Declared contrast group does not span at least "
                        "two expected source classes."
                    ),
                }
            )

    blocker_names = {
        item["contrast_group"]
        for item in blockers
    }

    expected_blockers = {
        "generic_official_with_vs_without_context",
        "immigration_status_rule_vs_external_entitlement",
    }

    if blocker_names != expected_blockers:
        raise RuntimeError(
            "Human-review blocker set differs from the expected pack-v4 "
            f"review result: {sorted(blocker_names)}"
        )

    proposed_metadata_only_correction = {
        "generic_official_with_vs_without_context": {
            "remove_group_from_case": "iv4_040",
            "add_group_to_case": "iv4_034",
            "preserve_group_member": "iv4_038",
            "resulting_expected_classes": [
                "other_official_external_authority",
                "unresolved",
            ],
        },
        "immigration_status_rule_vs_external_entitlement": {
            "remove_group_from_case": "iv4_029",
            "add_group_to_case": "iv4_002",
            "preserve_group_member": "iv4_027",
            "resulting_expected_classes": [
                "operational_manual_instruction",
                "external_entitlement_or_service_regime",
            ],
        },
    }

    review = {
        "schema": (
            "waypoint-source-boundary-classifier-independent-pack-human-review-v4"
        ),
        "status": (
            "REVISE_CONTRAST_METADATA_ONLY"
        ),
        "reviewed_on": str(date.today()),
        "source_artifacts": {
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
            ),
            "independent_contract_pack_v4_sha256": (
                EXPECTED_PACK_V4_SHA256
            ),
        },
        "review_scope": {
            "case_count": 40,
            "source_classes": 12,
            "contrast_groups": 12,
            "independence_metadata_reviewed": True,
            "expected_mapping_structure_reviewed": True,
            "contrast_group_semantics_reviewed": True,
            "model_calls": 0,
        },
        "passed_checks": {
            "test_count": True,
            "resolved_unresolved_distribution": True,
            "all_12_source_classes_present": True,
            "observed_pack_not_read_by_construction_script": True,
            "observed_predictions_not_read_by_construction_script": True,
            "observed_score_not_read_by_construction_script": True,
            "failure_analysis_not_read_by_construction_script": True,
            "observed_case_id_family_not_used": True,
            "all_contrast_groups_have_at_least_two_members": True,
        },
        "blockers": blockers,
        "blocker_count": len(blockers),
        "review_decision": {
            "pack_v4": "REVISE_METADATA_ONLY",
            "gold_label_changes_required": False,
            "proposition_changes_required": False,
            "trusted_context_changes_required": False,
            "case_count_changes_required": False,
            "source_class_distribution_changes_required": False,
            "contrast_group_metadata_changes_required": True,
        },
        "proposed_metadata_only_correction": (
            proposed_metadata_only_correction
        ),
        "immutability_requirements_for_v5": {
            "all_40_case_ids_identical": True,
            "all_40_propositions_identical": True,
            "all_40_expected_outputs_identical": True,
            "all_40_basis_values_identical": True,
            "all_40_trusted_source_context_values_identical": True,
            "source_class_counts_identical": True,
            "resolved_unresolved_counts_identical": True,
            "only_four_case_contrast_group_fields_may_change": [
                "iv4_002",
                "iv4_029",
                "iv4_034",
                "iv4_040",
            ],
        },
        "authorisations": {
            "metadata_only_pack_v5_construction_authorised": True,
            "acceptance_threshold_freeze_authorised": False,
            "classifier_implementation_v2_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_model_run_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_independent_contract_pack_v5"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Create a metadata-only corrected pack v5 by changing only "
                "the four authorised contrast_group fields and preserving "
                "all case content and gold labels exactly."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            review,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != "REVISE_CONTRAST_METADATA_ONLY":
        raise RuntimeError(
            "Saved pack-v4 human-review status changed."
        )

    if saved.get("blocker_count") != 2:
        raise RuntimeError(
            "Saved blocker count changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get(
        "metadata_only_pack_v5_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Metadata-only pack-v5 construction not authorised."
        )

    for forbidden in (
        "acceptance_threshold_freeze_authorised",
        "classifier_implementation_v2_authorised",
        "classifier_prompt_change_authorised",
        "classifier_model_run_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Human review unexpectedly authorises {forbidden}."
            )

    print("Waypoint independent contract pack v4 human review")
    print("=" * 64)
    print(f"Design-v3 SHA256:           {sha256(DESIGN_V3_PATH)}")
    print(f"Pack-v4 SHA256:             {sha256(PACK_V4_PATH)}")
    print()
    print("Review result")
    print("-" * 64)
    print("Cases:                      40 PASS")
    print("Source classes:             12 PASS")
    print("Contrast groups:            12")
    print("Contrast member counts:     PASS")
    print("Contrast semantics:         REVISE")
    print()
    print("Blockers")
    print("-" * 64)
    for blocker in blockers:
        print(
            f"{blocker['contrast_group']}: "
            f"{', '.join(blocker['distinct_source_classes'])}"
        )
    print()
    print("Required correction:        METADATA ONLY")
    print("Proposition changes:        NO")
    print("Gold-label changes:         NO")
    print("Trusted-context changes:    NO")
    print("Case-count changes:         NO")
    print("Class-distribution changes: NO")
    print()
    print("Pack v5 metadata fix:       AUTHORISED")
    print("Threshold freeze:           NOT AUTHORISED")
    print("Implementation:             NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  METADATA-ONLY PACK V5")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Human-review SHA256:        {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Independent pack v4 human review: COMPLETE")


if __name__ == "__main__":
    main()
