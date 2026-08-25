"""Create metadata-only corrected independent contract pack v5.

This script:
- reads frozen independent pack v4;
- reads the frozen v4 human review;
- changes ONLY four authorised contrast_group fields;
- preserves every case ID, proposition, expected output, basis, trusted source
  context, class distribution, and resolved/unresolved count exactly;
- makes NO model calls.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_independent_contract_pack_v5.py
    uv run python -m scripts.freeze_source_boundary_classifier_independent_contract_pack_v5

Output:
    tests/source_boundary_classifier_independent_contract_test_pack_v5.json
"""

from __future__ import annotations

import copy
import hashlib
import json
from collections import Counter, defaultdict
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

HUMAN_REVIEW_V4_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_pack_human_review_v4.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v5.json"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_PACK_V4_SHA256 = (
    "BC9515B3394E880C4FBEBD7C13F9A4FC"
    "43F7823EB484D30B3E008C3632C0304E"
)

EXPECTED_HUMAN_REVIEW_V4_SHA256 = (
    "1DA2FAD8EA80985E6FD9615F256F34EF"
    "227F4E2991D2159C24EB431203C95B17"
)

EXPECTED_TEST_COUNT = 40
EXPECTED_RESOLVED_COUNT = 34
EXPECTED_UNRESOLVED_COUNT = 6
EXPECTED_SOURCE_CLASS_COUNT = 12
EXPECTED_CONTRAST_GROUP_COUNT = 12

AUTHORISED_CHANGES = {
    "iv4_002": {
        "from": None,
        "to": "immigration_status_rule_vs_external_entitlement",
    },
    "iv4_029": {
        "from": "immigration_status_rule_vs_external_entitlement",
        "to": None,
    },
    "iv4_034": {
        "from": None,
        "to": "generic_official_with_vs_without_context",
    },
    "iv4_040": {
        "from": "generic_official_with_vs_without_context",
        "to": None,
    },
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
            "Refusing to create independent pack v5."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def index_tests(
    tests: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}

    for item in tests:
        case_id = item.get("case_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Invalid case_id.")

        if case_id in indexed:
            raise RuntimeError(
                f"Duplicate case_id: {case_id}"
            )

        indexed[case_id] = item

    return indexed


def canonical_without_contrast(
    item: dict[str, Any],
) -> dict[str, Any]:
    copy_item = copy.deepcopy(item)
    copy_item.pop("contrast_group", None)
    return copy_item


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Independent pack v5 already exists: {OUTPUT_PATH}\n"
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
    require_sha(
        HUMAN_REVIEW_V4_PATH,
        EXPECTED_HUMAN_REVIEW_V4_SHA256,
        "Frozen v4 human review",
    )

    design = load_json(DESIGN_V3_PATH)
    pack_v4 = load_json(PACK_V4_PATH)
    review_v4 = load_json(HUMAN_REVIEW_V4_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v3"
    ):
        raise RuntimeError("Unexpected design-v3 schema.")

    if pack_v4.get("schema") != (
        "waypoint-source-boundary-classifier-independent-contract-test-pack-v4"
    ):
        raise RuntimeError("Unexpected pack-v4 schema.")

    if review_v4.get("schema") != (
        "waypoint-source-boundary-classifier-independent-pack-human-review-v4"
    ):
        raise RuntimeError("Unexpected v4 human-review schema.")

    if review_v4.get("status") != (
        "REVISE_CONTRAST_METADATA_ONLY"
    ):
        raise RuntimeError(
            "V4 human review does not authorise metadata-only correction."
        )

    if review_v4.get(
        "authorisations",
        {},
    ).get(
        "metadata_only_pack_v5_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Metadata-only pack-v5 construction is not authorised."
        )

    immutable = review_v4.get(
        "immutability_requirements_for_v5",
        {},
    )

    if immutable.get(
        "only_four_case_contrast_group_fields_may_change"
    ) != [
        "iv4_002",
        "iv4_029",
        "iv4_034",
        "iv4_040",
    ]:
        raise RuntimeError(
            "V4 human-review authorised-change set changed."
        )

    tests_v4 = pack_v4.get("tests")

    if (
        not isinstance(tests_v4, list)
        or len(tests_v4) != EXPECTED_TEST_COUNT
    ):
        raise RuntimeError(
            "Frozen pack v4 must contain exactly 40 tests."
        )

    indexed_v4 = index_tests(tests_v4)

    if set(AUTHORISED_CHANGES) - set(indexed_v4):
        raise RuntimeError(
            "One or more authorised correction cases is missing."
        )

    for case_id, change in AUTHORISED_CHANGES.items():
        actual = indexed_v4[case_id].get("contrast_group")

        if actual != change["from"]:
            raise RuntimeError(
                f"{case_id}: frozen v4 contrast_group changed.\n"
                f"Expected: {change['from']!r}\n"
                f"Actual:   {actual!r}"
            )

    pack_v5 = copy.deepcopy(pack_v4)

    pack_v5["schema"] = (
        "waypoint-source-boundary-classifier-independent-contract-test-pack-v5"
    )
    pack_v5["status"] = (
        "FROZEN_METADATA_CORRECTED_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW"
    )
    pack_v5["frozen_on"] = str(date.today())

    pack_v5["source_artifacts"] = {
        "classifier_design_v3_sha256": (
            EXPECTED_DESIGN_V3_SHA256
        ),
        "independent_contract_pack_v4_sha256": (
            EXPECTED_PACK_V4_SHA256
        ),
        "independent_pack_human_review_v4_sha256": (
            EXPECTED_HUMAN_REVIEW_V4_SHA256
        ),
    }

    construction_v4 = pack_v4.get("construction")

    if not isinstance(construction_v4, dict):
        raise RuntimeError(
            "Frozen pack v4 is missing construction metadata."
        )

    construction_v5 = copy.deepcopy(construction_v4)
    construction_v5.update(
        {
            "revision_type": "metadata_only_contrast_group_correction",
            "source_pack": "v4",
            "source_pack_sha256": EXPECTED_PACK_V4_SHA256,
            "human_review_sha256": (
                EXPECTED_HUMAN_REVIEW_V4_SHA256
            ),
            "changed_case_count": 4,
            "changed_field": "contrast_group",
            "case_content_changed": False,
            "expected_outputs_changed": False,
            "basis_changed": False,
            "trusted_source_context_changed": False,
            "case_ids_changed": False,
            "source_class_distribution_changed": False,
            "resolved_unresolved_distribution_changed": False,
            "model_calls": 0,
        }
    )
    pack_v5["construction"] = construction_v5

    tests_v5 = pack_v5["tests"]
    indexed_v5 = index_tests(tests_v5)

    for case_id, change in AUTHORISED_CHANGES.items():
        indexed_v5[case_id]["contrast_group"] = change["to"]

    # Rebuild contrast coverage directly from the corrected tests.
    groups_v5: dict[str, list[str]] = defaultdict(list)

    for item in tests_v5:
        group = item.get("contrast_group")

        if isinstance(group, str) and group:
            groups_v5[group].append(item["case_id"])

    if len(groups_v5) != EXPECTED_CONTRAST_GROUP_COUNT:
        raise RuntimeError(
            f"Expected {EXPECTED_CONTRAST_GROUP_COUNT} corrected contrast "
            f"groups; found {len(groups_v5)}."
        )

    # Every declared contrast must now span at least two expected source classes.
    invalid_contrasts: dict[str, list[str]] = {}

    for group, members in groups_v5.items():
        classes = sorted(
            {
                indexed_v5[case_id]["expected"]["source_class"]
                for case_id in members
            }
        )

        if len(members) < 2 or len(classes) < 2:
            invalid_contrasts[group] = classes

    if invalid_contrasts:
        raise RuntimeError(
            "Corrected v5 still contains invalid contrasts: "
            f"{invalid_contrasts}"
        )

    expected_specific_groups = {
        "immigration_status_rule_vs_external_entitlement": {
            "operational_manual_instruction",
            "external_entitlement_or_service_regime",
        },
        "generic_official_with_vs_without_context": {
            "other_official_external_authority",
            "unresolved",
        },
    }

    for group, expected_classes in (
        expected_specific_groups.items()
    ):
        actual_classes = {
            indexed_v5[case_id]["expected"]["source_class"]
            for case_id in groups_v5[group]
        }

        if actual_classes != expected_classes:
            raise RuntimeError(
                f"{group}: corrected class contrast changed.\n"
                f"Expected: {sorted(expected_classes)}\n"
                f"Actual:   {sorted(actual_classes)}"
            )

    # Prove that only the four authorised contrast_group fields changed.
    if set(indexed_v4) != set(indexed_v5):
        raise RuntimeError(
            "V5 case-ID set differs from v4."
        )

    changed_cases: list[str] = []

    for case_id in sorted(indexed_v4):
        old_item = indexed_v4[case_id]
        new_item = indexed_v5[case_id]

        if canonical_without_contrast(
            old_item
        ) != canonical_without_contrast(
            new_item
        ):
            raise RuntimeError(
                f"{case_id}: non-contrast test content changed."
            )

        old_group = old_item.get("contrast_group")
        new_group = new_item.get("contrast_group")

        if old_group != new_group:
            changed_cases.append(case_id)

            if case_id not in AUTHORISED_CHANGES:
                raise RuntimeError(
                    f"{case_id}: unauthorised contrast_group change."
                )

            expected_change = AUTHORISED_CHANGES[case_id]

            if (
                old_group != expected_change["from"]
                or new_group != expected_change["to"]
            ):
                raise RuntimeError(
                    f"{case_id}: contrast_group change differs from "
                    "human-review authorisation."
                )

    if changed_cases != sorted(AUTHORISED_CHANGES):
        raise RuntimeError(
            "Changed-case set differs from the four authorised cases."
        )

    # Preserve all substantive distributions.
    class_counts_v4 = Counter(
        item["expected"]["source_class"]
        for item in tests_v4
    )
    class_counts_v5 = Counter(
        item["expected"]["source_class"]
        for item in tests_v5
    )

    if class_counts_v4 != class_counts_v5:
        raise RuntimeError(
            "Source-class distribution changed."
        )

    resolved_v4 = Counter(
        item["expected"]["resolution_status"]
        for item in tests_v4
    )
    resolved_v5 = Counter(
        item["expected"]["resolution_status"]
        for item in tests_v5
    )

    if resolved_v4 != resolved_v5:
        raise RuntimeError(
            "Resolved/unresolved distribution changed."
        )

    if resolved_v5 != Counter(
        {
            "resolved": EXPECTED_RESOLVED_COUNT,
            "unresolved": EXPECTED_UNRESOLVED_COUNT,
        }
    ):
        raise RuntimeError(
            "Unexpected corrected resolved/unresolved counts."
        )

    coverage_v4 = pack_v4.get("coverage")

    if not isinstance(coverage_v4, dict):
        raise RuntimeError(
            "Frozen v4 is missing coverage metadata."
        )

    coverage_v5 = copy.deepcopy(coverage_v4)
    coverage_v5["contrast_groups"] = dict(groups_v5)
    coverage_v5[
        "all_contrast_groups_span_multiple_source_classes"
    ] = True
    coverage_v5[
        "metadata_only_correction_verified"
    ] = True

    pack_v5["coverage"] = coverage_v5

    scoring_v4 = pack_v4.get("scoring_contract")

    if not isinstance(scoring_v4, dict):
        raise RuntimeError(
            "Frozen v4 is missing scoring contract."
        )

    pack_v5["scoring_contract"] = copy.deepcopy(
        scoring_v4
    )

    pack_v5["authorisations"] = {
        "human_review_authorised": True,
        "acceptance_threshold_freeze_authorised": False,
        "classifier_implementation_v2_authorised": False,
        "classifier_prompt_change_authorised": False,
        "classifier_model_run_authorised": False,
        "observed_pack_rerun_authorised": False,
        "candidate_v7_build_authorised": False,
        "production_runtime_change_authorised": False,
        "fresh_external_v3_holdout_authorised": False,
    }

    pack_v5["next_engineering_task"] = {
        "name": (
            "human_review_source_boundary_classifier_independent_pack_v5"
        ),
        "authorised": True,
        "model_calls": 0,
        "purpose": (
            "Verify the metadata-only correction and approve or reject "
            "pack v5 before freezing acceptance thresholds."
        ),
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            pack_v5,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_METADATA_CORRECTED_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Saved pack-v5 status changed."
        )

    if len(saved.get("tests", [])) != EXPECTED_TEST_COUNT:
        raise RuntimeError(
            "Saved pack-v5 case count changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get("human_review_authorised") is not True:
        raise RuntimeError(
            "Pack-v5 human review was not authorised."
        )

    for forbidden in (
        "acceptance_threshold_freeze_authorised",
        "classifier_implementation_v2_authorised",
        "classifier_prompt_change_authorised",
        "classifier_model_run_authorised",
        "observed_pack_rerun_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Pack v5 unexpectedly authorises {forbidden}."
            )

    print("Waypoint independent classifier contract pack v5 freeze")
    print("=" * 64)
    print(f"Design-v3 SHA256:           {sha256(DESIGN_V3_PATH)}")
    print(f"Pack-v4 SHA256:             {sha256(PACK_V4_PATH)}")
    print(
        f"V4 human-review SHA256:     "
        f"{sha256(HUMAN_REVIEW_V4_PATH)}"
    )
    print()
    print("Metadata-only correction")
    print("-" * 64)
    print("Changed cases:              4")
    print(
        "Changed case IDs:           "
        + ", ".join(changed_cases)
    )
    print("Changed field:              contrast_group ONLY")
    print("Case IDs changed:           NO")
    print("Propositions changed:       NO")
    print("Expected outputs changed:   NO")
    print("Basis changed:              NO")
    print("Trusted context changed:    NO")
    print("Class distribution changed: NO")
    print("Resolution counts changed:  NO")
    print()
    print("Corrected contrast semantics")
    print("-" * 64)
    print(
        "immigration_status_rule_vs_external_entitlement: PASS"
    )
    print(
        "generic_official_with_vs_without_context:       PASS"
    )
    print(
        "All 12 contrast groups multi-class:             PASS"
    )
    print()
    print("Tests:                      40")
    print("Resolved:                   34")
    print("Unresolved:                 6")
    print("Source classes:             12")
    print("Contrast groups:            12")
    print()
    print("Pack v5:                    FROZEN")
    print("Human review:               AUTHORISED")
    print("Threshold freeze:           NOT AUTHORISED")
    print("Implementation:             NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  HUMAN REVIEW PACK V5")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Pack-v5 SHA256:             {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Independent contract pack v5 freeze: PASS")


if __name__ == "__main__":
    main()
