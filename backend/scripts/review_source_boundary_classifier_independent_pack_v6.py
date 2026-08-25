"""Human review of Waypoint source-boundary classifier independent pack v6.

REVIEW/FREEZE ONLY.
- No model calls.
- No classifier implementation.
- No threshold changes.
- No prediction.
- Does not mutate pack v6.
- Reviews structural/gold/contrast validity AND independence from the already
  observed pack v5 and failure-analysis evidence.

Human-review conclusion:
- Structural/design-v4 coverage: PASS.
- Gold-label defect observed: NO.
- Contrast metadata: PASS.
- Freshness/independence: FAIL.
- Pack v6 must not be used as a fresh untouched acceptance pack.
- A genuinely new independent pack must be constructed before thresholds or
  implementation v3 are authorised.

Run from backend/:
    uv run python -m py_compile scripts/review_source_boundary_classifier_independent_pack_v6.py
    uv run python -m scripts.review_source_boundary_classifier_independent_pack_v6

Output:
    tests/source_boundary_classifier_independent_pack_human_review_v6.json
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

FAILURE_ANALYSIS_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_failure_analysis_v2.json"
)

PACK_V6_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v6.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_pack_human_review_v6.json"
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

EXPECTED_FAILURE_ANALYSIS_V2_SHA256 = (
    "DA353315AB3EB4CB409064BD850B42893"
    "F6D59590077BA4550152EC463294F06"
)

EXPECTED_PACK_V6_SHA256 = (
    "F1383D338CD64F6A7DB53C13934050CE"
    "BE87FAE4F41EE008C79A0EBB5199BCDE"
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

# Human-reviewed examples demonstrating that v6 is semantically derivative
# of the already observed acceptance pack. These are review evidence only,
# never runtime/prediction logic.
DERIVATIVE_PAIR_REVIEW = [
    {
        "old_case_id": "iv4_001",
        "new_case_id": "v6_001",
        "finding": (
            "Same core employer-change/visa-condition proposition, rephrased."
        ),
    },
    {
        "old_case_id": "iv4_008",
        "new_case_id": "v6_009",
        "finding": (
            "Same statutory-power proposition about immigration officers "
            "requiring information, with only scenario detail added."
        ),
    },
    {
        "old_case_id": "iv4_011",
        "new_case_id": "v6_013",
        "finding": (
            "Same current INZ processing-timeframe proposition, rephrased."
        ),
    },
    {
        "old_case_id": "iv4_021",
        "new_case_id": "v6_025",
        "finding": (
            "Same foreign civil-registry replacement-record issuing pattern."
        ),
    },
    {
        "old_case_id": "iv4_024",
        "new_case_id": "v6_029",
        "finding": (
            "Same government qualifications-assessment service pattern."
        ),
    },
    {
        "old_case_id": "iv4_027",
        "new_case_id": "v6_034",
        "finding": (
            "Same immigration-status/public-health-entitlement boundary."
        ),
    },
    {
        "old_case_id": "iv4_030",
        "new_case_id": "v6_037",
        "finding": (
            "Same professional-registration competence-assessment pattern."
        ),
    },
    {
        "old_case_id": "iv4_033",
        "new_case_id": "v6_041",
        "finding": (
            "Same foreign border electronic traveller-declaration pattern."
        ),
    },
    {
        "old_case_id": "iv4_034",
        "new_case_id": "v6_042",
        "finding": (
            "Same overseas customs reporting-procedure pattern."
        ),
    },
    {
        "old_case_id": "iv4_039",
        "new_case_id": "v6_047",
        "finding": (
            "Same ambiguity between current immigration charge and historical/"
            "legal amount."
        ),
    },
]

FAILURE_DERIVATIVE_REVIEW = [
    {
        "observed_failure_case_id": "iv4_026",
        "new_case_id": "v6_046",
        "finding": (
            "New unresolved case directly exercises the already-observed "
            "issuer-versus-independent-verification failure mechanism."
        ),
    },
    {
        "observed_failure_case_id": "iv4_036",
        "new_case_id": "v6_048",
        "finding": (
            "New unresolved case directly exercises the already-observed "
            "unspecified overseas official-owner/context-gate failure mechanism."
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
            "Refusing pack-v6 human review."
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
            raise RuntimeError(f"Duplicate case_id: {case_id}")

        indexed[case_id] = item

    return indexed


def token_set(text: str) -> set[str]:
    return set(
        re.findall(
            r"[a-z0-9]+",
            text.lower(),
        )
    )


def jaccard(a: str, b: str) -> float:
    left = token_set(a)
    right = token_set(b)

    if not left and not right:
        return 1.0

    union = left | right

    if not union:
        return 0.0

    return len(left & right) / len(union)


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Pack-v6 human review already exists: {OUTPUT_PATH}\n"
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
            "Approved classifier design-v4 human review",
        ),
        (
            PACK_V5_PATH,
            EXPECTED_PACK_V5_SHA256,
            "Observed independent pack v5",
        ),
        (
            FAILURE_ANALYSIS_V2_PATH,
            EXPECTED_FAILURE_ANALYSIS_V2_SHA256,
            "Frozen classifier failure analysis v2",
        ),
        (
            PACK_V6_PATH,
            EXPECTED_PACK_V6_SHA256,
            "Fresh-candidate independent pack v6",
        ),
    ):
        require_sha(path, expected_sha, label)

    design_v4 = load_json(DESIGN_V4_PATH)
    design_review = load_json(DESIGN_V4_REVIEW_PATH)
    pack_v5 = load_json(PACK_V5_PATH)
    failure_analysis = load_json(FAILURE_ANALYSIS_V2_PATH)
    pack_v6 = load_json(PACK_V6_PATH)

    if design_v4.get("schema") != (
        "waypoint-source-boundary-classifier-design-v4"
    ):
        raise RuntimeError("Unexpected design-v4 schema.")

    if design_review.get("status") != (
        "APPROVED_FRESH_INDEPENDENT_PACK_CONSTRUCTION_ONLY"
    ):
        raise RuntimeError(
            "Design-v4 review status changed."
        )

    if pack_v6.get("schema") != (
        "waypoint-source-boundary-classifier-independent-contract-test-pack-v6"
    ):
        raise RuntimeError("Unexpected pack-v6 schema.")

    if pack_v6.get("status") != (
        "FROZEN_FRESH_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Pack v6 is not frozen for human review."
        )

    if pack_v6.get(
        "authorisations",
        {},
    ).get(
        "fresh_pack_v6_human_review_authorised"
    ) is not True:
        raise RuntimeError(
            "Pack-v6 human review is not authorised."
        )

    tests_v5 = pack_v5.get("tests")
    tests_v6 = pack_v6.get("tests")

    if not isinstance(tests_v5, list):
        raise RuntimeError("Pack v5 tests missing.")

    if not isinstance(tests_v6, list) or len(tests_v6) != 50:
        raise RuntimeError(
            "Pack v6 must contain exactly 50 tests."
        )

    indexed_v5 = index_tests(tests_v5)
    indexed_v6 = index_tests(tests_v6)

    # Structural review.
    class_counts = Counter(
        item["expected"]["source_class"]
        for item in tests_v6
    )

    if dict(class_counts) != EXPECTED_CLASS_COUNTS:
        raise RuntimeError(
            "Pack-v6 source-class distribution changed."
        )

    resolved = sum(
        1
        for item in tests_v6
        if item["expected"]["resolution_status"] == "resolved"
    )

    unresolved = sum(
        1
        for item in tests_v6
        if item["expected"]["resolution_status"] == "unresolved"
    )

    if (resolved, unresolved) != (44, 6):
        raise RuntimeError(
            "Pack-v6 resolved/unresolved distribution changed."
        )

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in tests_v6:
        group = item.get("contrast_group")

        if isinstance(group, str) and group:
            groups[group].append(item)

    if len(groups) != 15:
        raise RuntimeError(
            f"Expected 15 contrast groups; found {len(groups)}."
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
            f"Pack-v6 invalid contrast groups: {invalid_groups}"
        )

    # Verify the two design-v4 failure mechanisms are present in the old
    # frozen failure analysis, so the independence conclusion is grounded.
    frozen_failure_ids = {
        item.get("case_id")
        for item in failure_analysis.get("failures", [])
    }

    if frozen_failure_ids != {"iv4_026", "iv4_036"}:
        raise RuntimeError(
            "Frozen failure-analysis case set changed."
        )

    # Human-reviewed derivative pairs must exist with unchanged expected class.
    derivative_evidence: list[dict[str, Any]] = []

    for pair in DERIVATIVE_PAIR_REVIEW:
        old_id = pair["old_case_id"]
        new_id = pair["new_case_id"]

        if old_id not in indexed_v5:
            raise RuntimeError(f"Old review case missing: {old_id}")

        if new_id not in indexed_v6:
            raise RuntimeError(f"New review case missing: {new_id}")

        old_prop = indexed_v5[old_id]["unsupported_proposition"]
        new_prop = indexed_v6[new_id]["unsupported_proposition"]

        derivative_evidence.append(
            {
                **pair,
                "old_source_class": (
                    indexed_v5[old_id]["expected"]["source_class"]
                ),
                "new_source_class": (
                    indexed_v6[new_id]["expected"]["source_class"]
                ),
                "token_jaccard": round(
                    jaccard(old_prop, new_prop),
                    3,
                ),
            }
        )

    failure_derivative_evidence: list[dict[str, Any]] = []

    for pair in FAILURE_DERIVATIVE_REVIEW:
        old_id = pair["observed_failure_case_id"]
        new_id = pair["new_case_id"]

        if old_id not in indexed_v5:
            raise RuntimeError(
                f"Observed failure case missing from pack v5: {old_id}"
            )

        if new_id not in indexed_v6:
            raise RuntimeError(
                f"New failure-derived review case missing: {new_id}"
            )

        failure_derivative_evidence.append(
            {
                **pair,
                "observed_failure_gold_class": (
                    indexed_v5[old_id]["expected"]["source_class"]
                ),
                "new_gold_class": (
                    indexed_v6[new_id]["expected"]["source_class"]
                ),
                "token_jaccard": round(
                    jaccard(
                        indexed_v5[old_id]["unsupported_proposition"],
                        indexed_v6[new_id]["unsupported_proposition"],
                    ),
                    3,
                ),
            }
        )

    # No gold defect was identified during the human content review. The
    # rejection is specifically an evaluation-independence defect.
    review = {
        "schema": (
            "waypoint-source-boundary-classifier-independent-pack-human-review-v6"
        ),
        "status": (
            "REJECTED_FRESHNESS_INDEPENDENCE_REBUILD_REQUIRED"
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
            "failure_analysis_v2_sha256": (
                EXPECTED_FAILURE_ANALYSIS_V2_SHA256
            ),
            "pack_v6_sha256": (
                EXPECTED_PACK_V6_SHA256
            ),
        },
        "review_decision": {
            "overall": "REJECT",
            "structural_contract": "PASS",
            "source_class_distribution": "PASS",
            "resolved_unresolved_distribution": "PASS",
            "gold_label_review": "PASS",
            "gold_pack_defect_observed": False,
            "context_gate_coverage": "PASS",
            "foreign_issuing_boundary_coverage": "PASS",
            "contrast_semantics": "PASS",
            "contrast_groups_valid": "15/15",
            "freshness_independence": "FAIL",
            "fresh_untouched_acceptance_claim_valid": False,
        },
        "independence_failure": {
            "decision": "FAIL",
            "reason": (
                "Pack v6 contains multiple propositions that are close "
                "semantic paraphrases of already-observed pack-v5 cases and "
                "contains new cases that directly instantiate the two failure "
                "mechanisms used to revise design v4. This conflicts with the "
                "approved requirement that the next acceptance pack be "
                "independent of pack-v5 case wording and failure-analysis "
                "literals."
            ),
            "derivative_pair_count_reviewed": len(
                derivative_evidence
            ),
            "derivative_pairs": derivative_evidence,
            "observed_failure_derived_pair_count": len(
                failure_derivative_evidence
            ),
            "observed_failure_derived_pairs": (
                failure_derivative_evidence
            ),
            "construction_provenance_claim_not_sufficient": True,
            "explanation": (
                "A construction script can truthfully report that it did not "
                "open the prior pack while still producing derivative cases. "
                "Human review must assess the resulting evaluation content, "
                "not only file-read provenance."
            ),
        },
        "methodological_disposition": {
            "pack_v6_role": "DEVELOPMENT_DIAGNOSTIC_ONLY",
            "pack_v6_may_be_used_for_debugging": True,
            "pack_v6_may_be_used_for_fresh_acceptance": False,
            "pack_v6_may_be_used_to_set_acceptance_thresholds": False,
            "pack_v6_may_be_used_for_model_prediction_acceptance": False,
            "thresholds_v2_remain_unchanged": True,
            "design_v4_remains_unchanged": True,
            "production_runtime_remains_unchanged": True,
        },
        "replacement_pack_requirements": {
            "name": (
                "source_boundary_classifier_independent_contract_test_pack_v7"
            ),
            "must_be_constructed_from": "classifier_design_v4",
            "must_not_read_during_construction": [
                "pack_v5",
                "pack_v6",
                "prior classifier predictions",
                "prior classifier scores",
                "failure analysis v2",
            ],
            "must_not_reuse": [
                "old proposition wording",
                "old scenario templates with superficial paraphrasing",
                "the two observed failure-case scenarios as direct test-case "
                "templates",
            ],
            "may_test_same_abstract_design_boundaries": True,
            "must_use_materially_different_scenarios": True,
            "must_cover_all_12_source_classes": True,
            "must_cover_all_three_context_gates": True,
            "must_cover_foreign_issuing_vs_external_agency_boundary": True,
            "must_include_conservative_unresolved_cases": True,
            "human_review_must_compare_content_against_prior_packs_after_freeze": True,
            "model_calls_during_construction": 0,
        },
        "authorisations": {
            "independent_pack_v7_construction_authorised": True,
            "independent_pack_v7_human_review_required": True,
            "acceptance_thresholds_v3_construction_authorised": False,
            "classifier_prompt_v3_construction_authorised": False,
            "classifier_implementation_v3_construction_authorised": False,
            "blind_input_v3_construction_authorised": False,
            "classifier_model_run_authorised": False,
            "classifier_rerun_on_pack_v5_authorised": False,
            "classifier_run_on_pack_v6_authorised": False,
            "threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_independent_contract_test_pack_v7"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Construct a genuinely new independent acceptance pack from "
                "design v4 using materially different scenarios, without "
                "reusing pack-v5/v6 wording or direct templates from the two "
                "observed failure cases."
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
        "REJECTED_FRESHNESS_INDEPENDENCE_REBUILD_REQUIRED"
    ):
        raise RuntimeError(
            "Saved pack-v6 human-review status changed."
        )

    saved_decision = saved.get(
        "review_decision",
        {},
    )

    if saved_decision.get("overall") != "REJECT":
        raise RuntimeError(
            "Saved pack-v6 human review did not preserve rejection."
        )

    if saved_decision.get(
        "freshness_independence"
    ) != "FAIL":
        raise RuntimeError(
            "Saved pack-v6 independence decision changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get(
        "independent_pack_v7_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Replacement independent-pack construction was not authorised."
        )

    for forbidden in (
        "acceptance_thresholds_v3_construction_authorised",
        "classifier_prompt_v3_construction_authorised",
        "classifier_implementation_v3_construction_authorised",
        "blind_input_v3_construction_authorised",
        "classifier_model_run_authorised",
        "classifier_rerun_on_pack_v5_authorised",
        "classifier_run_on_pack_v6_authorised",
        "threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Pack-v6 review unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier independent pack-v6 human review")
    print("=" * 78)
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
        f"Failure-analysis SHA256:    "
        f"{sha256(FAILURE_ANALYSIS_V2_PATH)}"
    )
    print(
        f"Pack-v6 SHA256:             "
        f"{sha256(PACK_V6_PATH)}"
    )
    print()
    print("Pack-v6 content review")
    print("-" * 78)
    print("Cases:                      50 PASS")
    print("Resolved/unresolved:        44/6 PASS")
    print("Source classes:             12/12 PASS")
    print("Contrast groups:            15/15 PASS")
    print("Gold-label defect observed: NO")
    print("Design-v4 coverage:         PASS")
    print("Context-gate coverage:      PASS")
    print("Foreign-issuer boundary:    PASS")
    print()
    print("Freshness / independence")
    print("-" * 78)
    print("Independence:               FAIL")
    print(
        f"Derivative old/new pairs:   "
        f"{len(derivative_evidence)} reviewed"
    )
    print(
        f"Failure-derived pairs:      "
        f"{len(failure_derivative_evidence)} reviewed"
    )
    print("Fresh untouched claim:      REJECTED")
    print()
    print("Pack-v6 role:               DEVELOPMENT/DIAGNOSTIC ONLY")
    print("Thresholds from pack-v6:    NOT AUTHORISED")
    print("Model run on pack-v6:       NOT AUTHORISED")
    print()
    print("Replacement pack-v7:        AUTHORISED")
    print("Pack-v7 human review:       REQUIRED")
    print("Threshold-v3 construction:  NOT AUTHORISED")
    print("Prompt-v3 construction:     NOT AUTHORISED")
    print("Implementation-v3:          NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  INDEPENDENT CONTRACT PACK V7")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(
        f"Pack-v6 review SHA256:      "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Independent pack-v6 human review: REJECT")


if __name__ == "__main__":
    main()
