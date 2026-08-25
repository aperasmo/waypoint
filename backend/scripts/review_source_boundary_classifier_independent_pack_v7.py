"""Human review of Waypoint source-boundary classifier independent pack v7.

REVIEW/FREEZE ONLY.
- No model calls.
- No classifier implementation.
- No threshold changes.
- No prediction.
- Does not mutate pack v7.
- Reviews structural validity and content-level independence against previously
  observed packs.
- Rejects pack v7 as a fresh untouched acceptance pack because several concrete
  scenario templates remain derivative of already observed pack-v6 cases.
- Does NOT authorise another ad-hoc replacement pack.
- Authorises construction of a pre-registered independent-pack construction
  protocol to prevent repeated trial-and-error evaluation-set generation.

Run from backend/:
    uv run python -m py_compile scripts/review_source_boundary_classifier_independent_pack_v7.py
    uv run python -m scripts.review_source_boundary_classifier_independent_pack_v7

Output:
    tests/source_boundary_classifier_independent_pack_human_review_v7.json
"""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

DESIGN_V4_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v4.json"
)

DESIGN_V4_REVIEW_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v4_human_review.json"
)

PACK_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v5.json"
)

PACK_V6_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v6.json"
)

PACK_V6_REVIEW_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_pack_human_review_v6.json"
)

PACK_V7_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v7.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_pack_human_review_v7.json"
)

EXPECTED_DESIGN_V4_SHA256 = (
    "9563158E74CFBC0C7D25D2DC2BA8FC20"
    "36E0B32193BADDFBE464ECCB99329948"
)

EXPECTED_DESIGN_V4_REVIEW_SHA256 = (
    "4456BEE89A249043510730BF5A01FCE05"
    "EF0A6C49EDF39FAD2EBBB55E17D9AD5"
)

EXPECTED_PACK_V5_SHA256 = (
    "1B3CEA56504E3932C7DCA342DF99DC225"
    "23A4676B1C22714B9A122DDD566E67B"
)

EXPECTED_PACK_V6_SHA256 = (
    "F1383D338CD64F6A7DB53C13934050CE"
    "BE87FAE4F41EE008C79A0EBB5199BCDE"
)

EXPECTED_PACK_V6_REVIEW_SHA256 = (
    "5A0B8C5E6C6C231710B50CE5A2D6A964"
    "8CECB18F2E8F07AACDF028BF0B4670C4"
)

EXPECTED_PACK_V7_SHA256 = (
    "EBD048AABBF30F2DCEAFCA8BBE69607B"
    "8ABFE2F906434BF8B333111950725F24"
)

EXPECTED_CLASS_COUNTS = {
    "operational_manual_instruction": 4,
    "manual_instruction_transition": 4,
    "legislation_or_regulation": 4,
    "inz_live_service_information": 4,
    "current_fee_or_charge_information": 4,
    "inz_non_manual_procedure_or_interpretation": 4,
    "foreign_issuing_authority_procedure": 4,
    "external_agency_assessment_or_service": 4,
    "external_entitlement_or_service_regime": 4,
    "professional_or_assessor_guidance": 4,
    "other_official_external_authority": 4,
    "unresolved": 6,
}

# These are human-review evidence pairs only. They are not model/runtime logic.
DERIVATIVE_PAIR_REVIEW = [
    {
        "prior_case_id": "v6_025",
        "new_case_id": "v7_025",
        "finding": (
            "Same concrete template: an authority explicitly identified as "
            "issuer of an official certificate provides a replacement "
            "certificate; only the certificate type changed."
        ),
    },
    {
        "prior_case_id": "v6_027",
        "new_case_id": "v7_026",
        "finding": (
            "Same concrete template: the authority that issued an identity/"
            "travel document prescribes replacement after loss or damage."
        ),
    },
    {
        "prior_case_id": "v6_030",
        "new_case_id": "v7_030",
        "finding": (
            "Near-direct reuse of a government identity-agency matching/"
            "verification service against official records."
        ),
    },
    {
        "prior_case_id": "v6_037",
        "new_case_id": "v7_037",
        "finding": (
            "Same concrete professional-registration template: evidence "
            "required from an overseas-trained practitioner for registration."
        ),
    },
    {
        "prior_case_id": "v6_045",
        "new_case_id": "v7_050",
        "finding": (
            "Same unresolved future-change template: an announced/circulated "
            "immigration change may or may not yet be an authoritative "
            "certified amendment because trusted certification context is "
            "absent."
        ),
    },
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(
    path: Path,
    expected_sha: str,
    label: str,
) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    actual = sha256(path)

    if actual != expected_sha:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected_sha}\n"
            f"Actual:   {actual}\n"
            "Refusing pack-v7 human review."
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
    result: dict[str, dict[str, Any]] = {}

    for item in tests:
        case_id = item.get("case_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Invalid case_id.")

        if case_id in result:
            raise RuntimeError(f"Duplicate case_id: {case_id}")

        result[case_id] = item

    return result


def token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def jaccard(left: str, right: str) -> float:
    a = token_set(left)
    b = token_set(right)

    if not a and not b:
        return 1.0

    union = a | b

    if not union:
        return 0.0

    return len(a & b) / len(union)


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Pack-v7 human review already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    for path, expected_sha, label in (
        (
            DESIGN_V4_PATH,
            EXPECTED_DESIGN_V4_SHA256,
            "Frozen classifier design v4",
        ),
        (
            DESIGN_V4_REVIEW_PATH,
            EXPECTED_DESIGN_V4_REVIEW_SHA256,
            "Approved design-v4 human review",
        ),
        (
            PACK_V5_PATH,
            EXPECTED_PACK_V5_SHA256,
            "Previously observed pack v5",
        ),
        (
            PACK_V6_PATH,
            EXPECTED_PACK_V6_SHA256,
            "Rejected pack v6",
        ),
        (
            PACK_V6_REVIEW_PATH,
            EXPECTED_PACK_V6_REVIEW_SHA256,
            "Frozen pack-v6 rejection review",
        ),
        (
            PACK_V7_PATH,
            EXPECTED_PACK_V7_SHA256,
            "Replacement pack v7",
        ),
    ):
        require_sha(path, expected_sha, label)

    design_v4 = load_json(DESIGN_V4_PATH)
    design_review = load_json(DESIGN_V4_REVIEW_PATH)
    pack_v5 = load_json(PACK_V5_PATH)
    pack_v6 = load_json(PACK_V6_PATH)
    pack_v6_review = load_json(PACK_V6_REVIEW_PATH)
    pack_v7 = load_json(PACK_V7_PATH)

    if design_v4.get("schema") != (
        "waypoint-source-boundary-classifier-design-v4"
    ):
        raise RuntimeError("Unexpected design-v4 schema.")

    if design_review.get("status") != (
        "APPROVED_FRESH_INDEPENDENT_PACK_CONSTRUCTION_ONLY"
    ):
        raise RuntimeError(
            "Design-v4 human-review status changed."
        )

    if pack_v6_review.get("status") != (
        "REJECTED_FRESHNESS_INDEPENDENCE_REBUILD_REQUIRED"
    ):
        raise RuntimeError(
            "Pack-v6 rejection status changed."
        )

    if pack_v7.get("schema") != (
        "waypoint-source-boundary-classifier-independent-contract-test-pack-v7"
    ):
        raise RuntimeError("Unexpected pack-v7 schema.")

    if pack_v7.get("status") != (
        "FROZEN_REPLACEMENT_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Pack v7 is not frozen for human review."
        )

    if pack_v7.get(
        "authorisations",
        {},
    ).get(
        "independent_pack_v7_human_review_authorised"
    ) is not True:
        raise RuntimeError(
            "Pack-v7 human review is not authorised."
        )

    tests_v5 = pack_v5.get("tests")
    tests_v6 = pack_v6.get("tests")
    tests_v7 = pack_v7.get("tests")

    if not isinstance(tests_v5, list):
        raise RuntimeError("Pack-v5 tests missing.")

    if not isinstance(tests_v6, list):
        raise RuntimeError("Pack-v6 tests missing.")

    if not isinstance(tests_v7, list) or len(tests_v7) != 50:
        raise RuntimeError(
            "Pack v7 must contain exactly 50 tests."
        )

    indexed_v6 = index_tests(tests_v6)
    indexed_v7 = index_tests(tests_v7)

    # Structural review.
    class_counts = Counter(
        item["expected"]["source_class"]
        for item in tests_v7
    )

    if dict(class_counts) != EXPECTED_CLASS_COUNTS:
        raise RuntimeError(
            "Pack-v7 source-class distribution changed."
        )

    resolved = sum(
        1
        for item in tests_v7
        if item["expected"]["resolution_status"] == "resolved"
    )

    unresolved = sum(
        1
        for item in tests_v7
        if item["expected"]["resolution_status"] == "unresolved"
    )

    if (resolved, unresolved) != (44, 6):
        raise RuntimeError(
            "Pack-v7 resolved/unresolved distribution changed."
        )

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in tests_v7:
        group = item.get("contrast_group")

        if isinstance(group, str) and group:
            groups[group].append(item)

    if len(groups) != 14:
        raise RuntimeError(
            f"Expected 14 contrast groups; found {len(groups)}."
        )

    invalid_groups: dict[str, list[str]] = {}

    for group, members in groups.items():
        classes = sorted(
            {
                member["expected"]["source_class"]
                for member in members
            }
        )

        if len(members) < 2 or len(classes) < 2:
            invalid_groups[group] = classes

    if invalid_groups:
        raise RuntimeError(
            f"Pack-v7 invalid contrast groups: {invalid_groups}"
        )

    derivative_evidence: list[dict[str, Any]] = []

    for pair in DERIVATIVE_PAIR_REVIEW:
        prior_id = pair["prior_case_id"]
        new_id = pair["new_case_id"]

        if prior_id not in indexed_v6:
            raise RuntimeError(
                f"Prior review case missing: {prior_id}"
            )

        if new_id not in indexed_v7:
            raise RuntimeError(
                f"New review case missing: {new_id}"
            )

        old_item = indexed_v6[prior_id]
        new_item = indexed_v7[new_id]

        derivative_evidence.append(
            {
                **pair,
                "prior_source_class": (
                    old_item["expected"]["source_class"]
                ),
                "new_source_class": (
                    new_item["expected"]["source_class"]
                ),
                "token_jaccard": round(
                    jaccard(
                        old_item["unsupported_proposition"],
                        new_item["unsupported_proposition"],
                    ),
                    3,
                ),
            }
        )

    review = {
        "schema": (
            "waypoint-source-boundary-classifier-independent-pack-human-review-v7"
        ),
        "status": (
            "REJECTED_FRESHNESS_PROTOCOL_REQUIRED"
        ),
        "reviewed_on": str(date.today()),
        "source_artifacts": {
            "classifier_design_v4_sha256": (
                EXPECTED_DESIGN_V4_SHA256
            ),
            "classifier_design_v4_human_review_sha256": (
                EXPECTED_DESIGN_V4_REVIEW_SHA256
            ),
            "observed_pack_v5_sha256": (
                EXPECTED_PACK_V5_SHA256
            ),
            "rejected_pack_v6_sha256": (
                EXPECTED_PACK_V6_SHA256
            ),
            "pack_v6_human_review_sha256": (
                EXPECTED_PACK_V6_REVIEW_SHA256
            ),
            "pack_v7_sha256": (
                EXPECTED_PACK_V7_SHA256
            ),
        },
        "review_decision": {
            "overall": "REJECT",
            "structural_contract": "PASS",
            "source_class_distribution": "PASS",
            "resolved_unresolved_distribution": "PASS",
            "gold_label_review": "PASS",
            "gold_pack_defect_observed": False,
            "design_v4_coverage": "PASS",
            "contrast_semantics": "PASS",
            "contrast_groups_valid": "14/14",
            "freshness_independence": "FAIL",
            "fresh_untouched_acceptance_claim_valid": False,
        },
        "independence_failure": {
            "decision": "FAIL",
            "reason": (
                "Although pack v7 uses new case IDs and several new domains, "
                "multiple cases still reuse concrete scenario templates from "
                "already observed pack-v6 cases with substituted entities or "
                "documents. Under the project's strict independence standard, "
                "that is insufficient for a fresh untouched acceptance claim."
            ),
            "reviewed_derivative_pair_count": (
                len(derivative_evidence)
            ),
            "reviewed_derivative_pairs": (
                derivative_evidence
            ),
            "same_abstract_boundary_testing_is_allowed": True,
            "same_concrete_scenario_template_with_noun_substitution_is_allowed": False,
        },
        "methodological_diagnosis": {
            "problem": (
                "AD_HOC_PACK_CONSTRUCTION_AFTER_PRIOR_CASE_INSPECTION"
            ),
            "design_v4_problem": False,
            "threshold_problem": False,
            "gold_label_problem": False,
            "classifier_problem_inferred_from_pack_v7": False,
            "reason_to_stop_immediate_pack_rebuilds": (
                "Repeated hand-authored replacement packs are being reviewed "
                "after construction and are reproducing observed scenario "
                "templates. Continuing directly to another pack would become "
                "evaluation-set trial-and-error."
            ),
        },
        "methodological_disposition": {
            "pack_v7_role": "DEVELOPMENT_DIAGNOSTIC_ONLY",
            "pack_v7_may_be_used_for_debugging": True,
            "pack_v7_may_be_used_for_fresh_acceptance": False,
            "pack_v7_may_be_used_to_set_acceptance_thresholds": False,
            "pack_v7_may_be_used_for_model_prediction_acceptance": False,
            "design_v4_remains_frozen": True,
            "acceptance_thresholds_v2_remain_frozen": True,
            "production_runtime_remains_unchanged": True,
        },
        "independent_pack_construction_protocol_requirements": {
            "protocol_name": (
                "source_boundary_classifier_independent_pack_construction_protocol_v1"
            ),
            "must_be_frozen_before_next_pack": True,
            "must_predefine_scenario_family_generation_rules": True,
            "must_predefine_exclusion_rules_for_observed_scenario_templates": True,
            "must_predefine_case_count_and_class_balance": True,
            "must_predefine_context_gate_coverage": True,
            "must_predefine_contrast_construction_rules": True,
            "must_predefine_independence_review_method": True,
            "must_predefine_rejection_criteria_before_next_pack_exists": True,
            "must_not_contain_future_gold_case_wording": True,
            "must_not_construct_next_pack_during_protocol_freeze": True,
            "must_not_authorise_model_prediction": True,
        },
        "authorisations": {
            "independent_pack_construction_protocol_v1_authorised": True,
            "replacement_pack_v8_construction_authorised": False,
            "acceptance_thresholds_v3_construction_authorised": False,
            "classifier_prompt_v3_construction_authorised": False,
            "classifier_implementation_v3_construction_authorised": False,
            "blind_input_v3_construction_authorised": False,
            "classifier_model_run_authorised": False,
            "classifier_rerun_on_pack_v5_authorised": False,
            "classifier_run_on_pack_v6_authorised": False,
            "classifier_run_on_pack_v7_authorised": False,
            "threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_independent_pack_construction_protocol_v1"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Pre-register how the next independent acceptance pack will be "
                "generated and rejected or approved before any future pack "
                "content exists, preventing further ad-hoc evaluation-set "
                "trial-and-error."
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

    if saved.get("status") != (
        "REJECTED_FRESHNESS_PROTOCOL_REQUIRED"
    ):
        raise RuntimeError(
            "Saved pack-v7 human-review status changed."
        )

    if saved.get(
        "review_decision",
        {},
    ).get("overall") != "REJECT":
        raise RuntimeError(
            "Saved pack-v7 review decision changed."
        )

    if saved.get(
        "review_decision",
        {},
    ).get(
        "freshness_independence"
    ) != "FAIL":
        raise RuntimeError(
            "Saved pack-v7 independence decision changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get(
        "independent_pack_construction_protocol_v1_authorised"
    ) is not True:
        raise RuntimeError(
            "Independent-pack construction protocol was not authorised."
        )

    for forbidden in (
        "replacement_pack_v8_construction_authorised",
        "acceptance_thresholds_v3_construction_authorised",
        "classifier_prompt_v3_construction_authorised",
        "classifier_implementation_v3_construction_authorised",
        "blind_input_v3_construction_authorised",
        "classifier_model_run_authorised",
        "classifier_rerun_on_pack_v5_authorised",
        "classifier_run_on_pack_v6_authorised",
        "classifier_run_on_pack_v7_authorised",
        "threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Pack-v7 review unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier independent pack-v7 human review")
    print("=" * 80)
    print(
        f"Design-v4 SHA256:           "
        f"{sha256(DESIGN_V4_PATH)}"
    )
    print(
        f"Design-v4 review SHA256:    "
        f"{sha256(DESIGN_V4_REVIEW_PATH)}"
    )
    print(
        f"Observed pack-v5 SHA256:    "
        f"{sha256(PACK_V5_PATH)}"
    )
    print(
        f"Rejected pack-v6 SHA256:    "
        f"{sha256(PACK_V6_PATH)}"
    )
    print(
        f"Pack-v6 review SHA256:      "
        f"{sha256(PACK_V6_REVIEW_PATH)}"
    )
    print(
        f"Pack-v7 SHA256:             "
        f"{sha256(PACK_V7_PATH)}"
    )
    print()
    print("Pack-v7 content review")
    print("-" * 80)
    print("Cases:                      50 PASS")
    print("Resolved/unresolved:        44/6 PASS")
    print("Source classes:             12/12 PASS")
    print("Contrast groups:            14/14 PASS")
    print("Gold-label defect observed: NO")
    print("Design-v4 coverage:         PASS")
    print()
    print("Freshness / independence")
    print("-" * 80)
    print("Independence:               FAIL")
    print(
        f"Derivative template pairs:  "
        f"{len(derivative_evidence)} reviewed"
    )
    print("Fresh untouched claim:      REJECTED")
    print()
    print("Methodological diagnosis")
    print("-" * 80)
    print("Design-v4 problem:          NO")
    print("Threshold problem:          NO")
    print("Gold-label problem:         NO")
    print("Problem:                    AD-HOC PACK CONSTRUCTION")
    print("Another immediate pack:     NOT AUTHORISED")
    print()
    print("Pack-v7 role:               DEVELOPMENT/DIAGNOSTIC ONLY")
    print("Model run on pack-v7:       NOT AUTHORISED")
    print("Thresholds from pack-v7:    NOT AUTHORISED")
    print()
    print("Independent-pack protocol:  AUTHORISED")
    print("Replacement pack-v8:        NOT AUTHORISED")
    print("Threshold-v3 construction:  NOT AUTHORISED")
    print("Prompt-v3 construction:     NOT AUTHORISED")
    print("Implementation-v3:          NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  INDEPENDENT-PACK CONSTRUCTION PROTOCOL V1")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(
        f"Pack-v7 review SHA256:      "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Independent pack-v7 human review: REJECT")


if __name__ == "__main__":
    main()
