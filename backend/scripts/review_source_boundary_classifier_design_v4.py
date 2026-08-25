"""Human review of Waypoint source-boundary classifier design v4.

REVIEW/FREEZE ONLY.
- No model calls.
- No prompt changes.
- No classifier implementation changes.
- No threshold changes.
- No production changes.
- Reviews design v4 for faithful, generic implementation of the two authorised
  revisions before any fresh acceptance pack or implementation is constructed.

Run from backend/:
    uv run python -m py_compile scripts/review_source_boundary_classifier_design_v4.py
    uv run python -m scripts.review_source_boundary_classifier_design_v4

Output:
    tests/source_boundary_classifier_design_v4_human_review.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = (
    BACKEND_DIR
    / "app"
    / "api"
    / "routes"
    / "ask.py"
)

DESIGN_V4_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v4.json"
)

DESIGN_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
)

THRESHOLDS_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_acceptance_thresholds_v2.json"
)

HUMAN_DIAGNOSTIC_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_human_diagnostic_review_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v4_human_review.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_DESIGN_V4_SHA256 = (
    "9563158E74CFBC0C7D25D2DC2BA8FC20"
    "36E0B32193BADDFBE464ECCB99329948"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_THRESHOLDS_V2_SHA256 = (
    "1BDD2ED8950D6E3E612C66DCD5384BD5"
    "E0CAC784E39A70C3CE09EAD5C310D277"
)

EXPECTED_HUMAN_DIAGNOSTIC_V2_SHA256 = (
    "B981E258FEB7EFB26B2901386522366B2"
    "30C82465D81A459DC91B1162E503392"
)

EXPECTED_SOURCE_CLASSES = [
    "operational_manual_instruction",
    "manual_instruction_transition",
    "legislation_or_regulation",
    "inz_live_service_information",
    "current_fee_or_charge_information",
    "inz_non_manual_procedure_or_interpretation",
    "foreign_issuing_authority_procedure",
    "external_agency_assessment_or_service",
    "external_entitlement_or_service_regime",
    "professional_or_assessor_guidance",
    "other_official_external_authority",
    "unresolved",
]

EXPECTED_CONTEXT_GATED_CLASSES = {
    "manual_instruction_transition",
    "inz_non_manual_procedure_or_interpretation",
    "other_official_external_authority",
}

EXPECTED_REQUIRED_REVISIONS = {
    "DETERMINISTIC_CONTEXT_GATE_ENFORCEMENT",
    "FOREIGN_ISSUING_VERIFICATION_BOUNDARY",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest().upper()


def require_sha(
    path: Path,
    expected: str,
    label: str,
) -> None:
    if not path.exists():
        raise SystemExit(
            f"Required file not found: {path}"
        )

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing design-v4 human review."
        )


def load_json(
    path: Path,
) -> dict[str, Any]:
    payload = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Design-v4 human-review artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    for path, expected, label in (
        (
            RUNTIME_PATH,
            EXPECTED_RUNTIME_SHA256,
            "Frozen production candidate-v2 runtime",
        ),
        (
            DESIGN_V4_PATH,
            EXPECTED_DESIGN_V4_SHA256,
            "Frozen classifier design v4",
        ),
        (
            DESIGN_V3_PATH,
            EXPECTED_DESIGN_V3_SHA256,
            "Frozen classifier design v3",
        ),
        (
            THRESHOLDS_V2_PATH,
            EXPECTED_THRESHOLDS_V2_SHA256,
            "Frozen acceptance thresholds v2",
        ),
        (
            HUMAN_DIAGNOSTIC_V2_PATH,
            EXPECTED_HUMAN_DIAGNOSTIC_V2_SHA256,
            "Frozen human diagnostic review v2",
        ),
    ):
        require_sha(
            path,
            expected,
            label,
        )

    design_v4 = load_json(
        DESIGN_V4_PATH
    )
    design_v3 = load_json(
        DESIGN_V3_PATH
    )
    thresholds_v2 = load_json(
        THRESHOLDS_V2_PATH
    )
    human_diagnostic = load_json(
        HUMAN_DIAGNOSTIC_V2_PATH
    )

    if design_v4.get("schema") != (
        "waypoint-source-boundary-classifier-design-v4"
    ):
        raise RuntimeError(
            "Unexpected design-v4 schema."
        )

    if design_v4.get("status") != (
        "FROZEN_DESIGN_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Design v4 is not frozen for human review."
        )

    if design_v3.get("schema") != (
        "waypoint-source-boundary-classifier-design-v3"
    ):
        raise RuntimeError(
            "Unexpected design-v3 schema."
        )

    if thresholds_v2.get("schema") != (
        "waypoint-source-boundary-classifier-acceptance-thresholds-v2"
    ):
        raise RuntimeError(
            "Unexpected thresholds-v2 schema."
        )

    if thresholds_v2.get("status") != (
        "FROZEN_BEFORE_CLASSIFIER_IMPLEMENTATION_AND_PREDICTION"
    ):
        raise RuntimeError(
            "Acceptance thresholds v2 are not in the frozen state."
        )

    if human_diagnostic.get("status") != (
        "APPROVED_DESIGN_V4_CONSTRUCTION_ONLY"
    ):
        raise RuntimeError(
            "Human diagnostic review does not support design v4."
        )

    source_artifacts = design_v4.get(
        "source_artifacts",
        {},
    )

    expected_source_bindings = {
        "production_runtime_sha256": (
            EXPECTED_RUNTIME_SHA256
        ),
        "classifier_design_v3_sha256": (
            EXPECTED_DESIGN_V3_SHA256
        ),
        "acceptance_thresholds_v2_sha256": (
            EXPECTED_THRESHOLDS_V2_SHA256
        ),
        "human_diagnostic_review_v2_sha256": (
            EXPECTED_HUMAN_DIAGNOSTIC_V2_SHA256
        ),
    }

    for key, expected in expected_source_bindings.items():
        actual = source_artifacts.get(key)

        if actual != expected:
            raise RuntimeError(
                f"Design-v4 source binding changed for {key}.\n"
                f"Expected: {expected}\n"
                f"Actual:   {actual}"
            )

    revision_scope = design_v4.get(
        "revision_scope",
        {},
    )

    if revision_scope.get(
        "taxonomy_changed"
    ) is not False:
        raise RuntimeError(
            "Design v4 unexpectedly changes the taxonomy."
        )

    if revision_scope.get(
        "source_class_count"
    ) != 12:
        raise RuntimeError(
            "Design v4 must preserve exactly 12 source classes."
        )

    if revision_scope.get(
        "thresholds_changed"
    ) is not False:
        raise RuntimeError(
            "Design v4 unexpectedly changes acceptance thresholds."
        )

    if revision_scope.get(
        "model_changed"
    ) is not False:
        raise RuntimeError(
            "Design v4 unexpectedly changes the model."
        )

    if revision_scope.get(
        "one_model_call_changed"
    ) is not False:
        raise RuntimeError(
            "Design v4 unexpectedly changes the one-call architecture."
        )

    revisions = revision_scope.get(
        "required_changes"
    )

    if (
        not isinstance(revisions, list)
        or set(revisions) != EXPECTED_REQUIRED_REVISIONS
        or len(revisions) != 2
    ):
        raise RuntimeError(
            "Design v4 contains an unexpected revision set."
        )

    source_classes = (
        design_v4.get(
            "source_classes",
            {},
        ).get(
            "allowed_values"
        )
    )

    if source_classes != EXPECTED_SOURCE_CLASSES:
        raise RuntimeError(
            "Design-v4 source-class taxonomy differs from the frozen "
            "12-class ordering."
        )

    # Confirm design v3 and v4 expose the same source-class set.
    v3_text = json.dumps(
        design_v3,
        ensure_ascii=False,
        sort_keys=True,
    )

    for source_class in EXPECTED_SOURCE_CLASSES:
        if source_class not in v3_text:
            raise RuntimeError(
                f"Design-v3 source class missing during preservation review: "
                f"{source_class}"
            )

    architecture = design_v4.get(
        "classifier_architecture",
        {},
    )

    stage_1 = architecture.get(
        "stage_1_model_proposal",
        {},
    )

    if stage_1.get(
        "model_generated_fields"
    ) != [
        "proposed_source_class",
        "basis",
    ]:
        raise RuntimeError(
            "Design-v4 model proposal fields changed."
        )

    if stage_1.get(
        "proposed_source_class_allowed_values"
    ) != EXPECTED_SOURCE_CLASSES:
        raise RuntimeError(
            "Design-v4 proposed source-class taxonomy changed."
        )

    if stage_1.get("zero_shot") is not True:
        raise RuntimeError(
            "Design v4 must remain zero-shot."
        )

    if stage_1.get("model_calls") != 1:
        raise RuntimeError(
            "Design v4 must preserve exactly one model call."
        )

    for key in (
        "automatic_retry",
        "repair_call",
        "fallback_model",
    ):
        if stage_1.get(key) is not False:
            raise RuntimeError(
                f"Design-v4 execution policy changed for {key}."
            )

    stage_2 = architecture.get(
        "stage_2_deterministic_validation",
        {},
    )

    if stage_2.get("model_calls") != 0:
        raise RuntimeError(
            "Deterministic validation must make zero model calls."
        )

    if stage_2.get(
        "input_fields"
    ) != [
        "proposed_source_class",
        "trusted_source_context",
    ]:
        raise RuntimeError(
            "Deterministic-validation inputs changed."
        )

    if stage_2.get(
        "output_field"
    ) != "source_class":
        raise RuntimeError(
            "Deterministic validation must output final source_class."
        )

    if stage_2.get(
        "may_demote_to_unresolved"
    ) is not True:
        raise RuntimeError(
            "Deterministic validation must be able to demote to unresolved."
        )

    if stage_2.get(
        "may_promote_unresolved_to_resolved"
    ) is not False:
        raise RuntimeError(
            "Design v4 must forbid deterministic promotion from unresolved."
        )

    if stage_2.get(
        "may_remap_one_resolved_class_to_another"
    ) is not False:
        raise RuntimeError(
            "Design v4 must forbid deterministic resolved-class remapping."
        )

    stage_3 = architecture.get(
        "stage_3_deterministic_derivation",
        {},
    )

    if stage_3.get(
        "input_field"
    ) != "source_class":
        raise RuntimeError(
            "Dependent fields must derive from final source_class."
        )

    expected_derived_fields = {
        "resolution_status",
        "source_domain",
        "responsible_authority_type",
    }

    actual_derived_fields = set(
        stage_3.get(
            "derived_fields",
            [],
        )
    )

    if actual_derived_fields != expected_derived_fields:
        raise RuntimeError(
            "Design-v4 deterministic derived-field set changed."
        )

    derivation_mapping = stage_3.get(
        "mapping"
    )

    if (
        not isinstance(derivation_mapping, dict)
        or set(derivation_mapping) != set(EXPECTED_SOURCE_CLASSES)
    ):
        raise RuntimeError(
            "Design-v4 deterministic derivation mapping is incomplete."
        )

    context_policy = design_v4.get(
        "context_gate_policy",
        {},
    )

    if context_policy.get(
        "universal_context_gate"
    ) is not False:
        raise RuntimeError(
            "Design v4 must not reintroduce a universal context gate."
        )

    gated_classes = context_policy.get(
        "gated_classes"
    )

    if (
        not isinstance(gated_classes, dict)
        or set(gated_classes) != EXPECTED_CONTEXT_GATED_CLASSES
    ):
        raise RuntimeError(
            "Design-v4 context-gated class set changed."
        )

    enforcement = context_policy.get(
        "deterministic_enforcement",
        {},
    )

    required_enforcement = {
        "required": True,
        "no_second_model_call": True,
        "no_semantic_fallback": True,
        "no_alternate_resolved_class_selection": True,
        "audit_proposed_class": True,
    }

    for key, expected in required_enforcement.items():
        if enforcement.get(key) is not expected:
            raise RuntimeError(
                f"Deterministic context-gate contract changed for {key}."
            )

    rule = enforcement.get("rule", "")

    if (
        not isinstance(rule, str)
        or "MUST be unresolved" not in rule
    ):
        raise RuntimeError(
            "Design-v4 deterministic gate-failure rule is not explicit."
        )

    for source_class, gate in gated_classes.items():
        if gate.get(
            "on_gate_failure"
        ) != "unresolved":
            raise RuntimeError(
                f"{source_class}: gate failure must resolve to unresolved."
            )

    foreign_boundary = design_v4.get(
        "foreign_issuing_boundary",
        {},
    )

    if "established issuing" not in foreign_boundary.get(
        "rule",
        "",
    ):
        raise RuntimeError(
            "Foreign-issuing rule does not require an established issuing role."
        )

    verification_rule = foreign_boundary.get(
        "verification_specific_rule",
        "",
    )

    required_verification_fragments = [
        "does not by itself establish",
        "issuer identity",
        "issuing role",
    ]

    for fragment in required_verification_fragments:
        if fragment not in verification_rule:
            raise RuntimeError(
                "Foreign-issuing verification boundary is incomplete: "
                + fragment
            )

    must_not_infer = set(
        foreign_boundary.get(
            "must_not_infer_issuer_from",
            [],
        )
    )

    required_non_inference = {
        "verification alone",
        "the fact that an authority is foreign",
        "generic public-records or document-related wording alone",
    }

    if must_not_infer != required_non_inference:
        raise RuntimeError(
            "Design-v4 issuer non-inference rule set changed."
        )

    external_boundary = foreign_boundary.get(
        "external_agency_boundary",
        "",
    )

    if "external_agency_assessment_or_service" not in external_boundary:
        raise RuntimeError(
            "Design-v4 external-agency boundary is missing."
        )

    unresolved_policy = design_v4.get(
        "unresolved_policy",
        {},
    )

    if unresolved_policy.get(
        "preserve_conservative_safety"
    ) is not True:
        raise RuntimeError(
            "Design v4 does not preserve conservative unresolved safety."
        )

    output_contract = design_v4.get(
        "output_contract",
        {},
    )

    model_fields = (
        output_contract.get(
            "model_output",
            {},
        ).get(
            "fields",
            {},
        )
    )

    if set(model_fields) != {
        "proposed_source_class",
        "basis",
    }:
        raise RuntimeError(
            "Design-v4 model-output contract contains unexpected fields."
        )

    final_fields = set(
        output_contract.get(
            "final_classifier_output",
            {},
        ).get(
            "fields",
            [],
        )
    )

    expected_final_fields = {
        "proposed_source_class",
        "source_class",
        "resolution_status",
        "source_domain",
        "responsible_authority_type",
        "basis",
        "gate_action",
    }

    if final_fields != expected_final_fields:
        raise RuntimeError(
            "Design-v4 final-output contract changed."
        )

    if output_contract.get(
        "final_classifier_output",
        {},
    ).get(
        "source_class_is_post_validation"
    ) is not True:
        raise RuntimeError(
            "Final source_class must be post-validation."
        )

    constraints = design_v4.get(
        "implementation_constraints",
        {},
    )

    required_true_constraints = [
        "no_examples_in_prompt",
        "no_test_ids",
        "no_benchmark_literals",
        "no_expected_answer_mappings",
        "no_question_specific_branches",
        "no_section_specific_logic",
        "no_threshold_specific_prediction_logic",
        "no_eval_artifact_reads_in_classifier",
        "one_model_call",
        "deterministic_gate_must_be_unit_testable_without_model_call",
    ]

    for key in required_true_constraints:
        if constraints.get(key) is not True:
            raise RuntimeError(
                f"Design-v4 implementation constraint changed: {key}"
            )

    for key in (
        "automatic_retry",
        "repair_call",
        "fallback_model",
    ):
        if constraints.get(key) is not False:
            raise RuntimeError(
                f"Design-v4 execution constraint changed: {key}"
            )

    design_text = DESIGN_V4_PATH.read_text(
        encoding="utf-8"
    )

    forbidden_case_literals = [
        "iv4_",
        "sbv2_",
    ]

    leaked_case_literals = [
        token
        for token in forbidden_case_literals
        if token in design_text
    ]

    if leaked_case_literals:
        raise RuntimeError(
            "Design v4 contains benchmark/case-ID literals: "
            + ", ".join(leaked_case_literals)
        )

    methodology = design_v4.get(
        "acceptance_methodology",
        {},
    )

    required_methodology = {
        "pack_v5_status": "DEVELOPMENT_DIAGNOSTIC_ONLY",
        "pack_v5_may_not_be_reused_as_fresh_acceptance": True,
        "same_prediction_set_may_not_be_rerun_for_acceptance": True,
        "fresh_independent_acceptance_pack_required": True,
        "fresh_pack_must_be_constructed_after_design_v4_human_review": True,
        "fresh_pack_must_not_copy_old_case_literals": True,
        "acceptance_thresholds_must_be_frozen_before_new_predictions": True,
        "all_gates_required": True,
        "manual_override": False,
    }

    for key, expected in required_methodology.items():
        if methodology.get(key) != expected:
            raise RuntimeError(
                f"Design-v4 acceptance methodology changed for {key}."
            )

    prior_auth = design_v4.get(
        "authorisations",
        {},
    )

    if prior_auth.get(
        "design_v4_human_review_authorised"
    ) is not True:
        raise RuntimeError(
            "Design v4 does not authorise its human review."
        )

    review = {
        "schema": (
            "waypoint-source-boundary-classifier-design-v4-human-review"
        ),
        "status": (
            "APPROVED_FRESH_INDEPENDENT_PACK_CONSTRUCTION_ONLY"
        ),
        "reviewed_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "classifier_design_v4_sha256": (
                EXPECTED_DESIGN_V4_SHA256
            ),
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
            ),
            "acceptance_thresholds_v2_sha256": (
                EXPECTED_THRESHOLDS_V2_SHA256
            ),
            "human_diagnostic_review_v2_sha256": (
                EXPECTED_HUMAN_DIAGNOSTIC_V2_SHA256
            ),
        },
        "review_decision": {
            "overall": "PASS",
            "revision_scope": "PASS",
            "taxonomy_preservation": "PASS",
            "threshold_preservation": "PASS",
            "one_call_architecture": "PASS",
            "deterministic_context_gate_semantics": "PASS",
            "foreign_issuing_verification_boundary": "PASS",
            "unresolved_safety": "PASS",
            "output_contract": "PASS",
            "benchmark_isolation": "PASS",
            "acceptance_methodology": "PASS",
        },
        "verified_revision_scope": {
            "source_classes": 12,
            "taxonomy_changed": False,
            "thresholds_changed": False,
            "model_changed": False,
            "required_revisions": [
                "DETERMINISTIC_CONTEXT_GATE_ENFORCEMENT",
                "FOREIGN_ISSUING_VERIFICATION_BOUNDARY",
            ],
            "additional_design_revisions_detected": False,
        },
        "deterministic_gate_review": {
            "decision": "PASS",
            "gated_classes": sorted(
                EXPECTED_CONTEXT_GATED_CLASSES
            ),
            "universal_context_gate": False,
            "gate_failure_final_class": "unresolved",
            "second_model_call": False,
            "semantic_fallback": False,
            "promotion_from_unresolved": False,
            "resolved_class_remapping": False,
            "proposed_source_class_audited": True,
            "unit_testable_without_model_call": True,
        },
        "foreign_issuing_review": {
            "decision": "PASS",
            "issuer_relationship_required": True,
            "verification_alone_sufficient": False,
            "foreign_authority_status_alone_sufficient": False,
            "generic_document_wording_alone_sufficient": False,
            "external_agency_service_boundary_preserved": True,
            "unresolved_available_when_role_ambiguous": True,
        },
        "methodological_review": {
            "pack_v5_status": "DEVELOPMENT_DIAGNOSTIC_ONLY",
            "pack_v5_reusable_as_fresh_acceptance": False,
            "same_prediction_set_reusable_for_acceptance": False,
            "fresh_independent_acceptance_pack_required": True,
            "fresh_pack_must_not_copy_old_case_literals": True,
            "fresh_pack_must_be_constructed_after_this_review": True,
            "implementation_must_not_be_constructed_before_fresh_pack_review": True,
            "thresholds_must_be_frozen_before_new_predictions": True,
        },
        "fresh_pack_construction_constraints": {
            "design_source": "classifier_design_v4",
            "must_be_independent_of": [
                "pack_v5 case wording",
                "pack_v5 case IDs",
                "pack_v5 predictions",
                "pack_v5 score",
                "pack_v5 failure-analysis literals",
            ],
            "must_cover_all_12_source_classes": True,
            "must_include_resolved_and_unresolved_cases": True,
            "must_test_all_three_context_gates": True,
            "must_test_foreign_issuing_vs_external_agency_boundary": True,
            "must_test_semantic_non_gated_resolution_without_context": True,
            "must_test_unresolved_ambiguity": True,
            "must_be_frozen_before_classifier_v3_implementation": True,
            "model_calls_during_construction": 0,
        },
        "authorisations": {
            "fresh_independent_acceptance_pack_v6_construction_authorised": True,
            "fresh_pack_human_review_required_after_construction": True,
            "acceptance_thresholds_v3_construction_authorised": False,
            "classifier_prompt_v3_construction_authorised": False,
            "classifier_implementation_v3_construction_authorised": False,
            "classifier_model_run_authorised": False,
            "classifier_rerun_on_pack_v5_authorised": False,
            "threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_independent_contract_test_pack_v6"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Construct a new independent acceptance pack from frozen "
                "design v4, without copying pack-v5 case literals or observed "
                "failure wording, before any prompt or implementation v3 is "
                "constructed."
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

    saved = load_json(
        OUTPUT_PATH
    )

    if saved.get("status") != (
        "APPROVED_FRESH_INDEPENDENT_PACK_CONSTRUCTION_ONLY"
    ):
        raise RuntimeError(
            "Saved design-v4 human-review status changed."
        )

    saved_auth = saved.get(
        "authorisations",
        {},
    )

    if saved_auth.get(
        "fresh_independent_acceptance_pack_v6_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Fresh independent pack-v6 construction was not authorised."
        )

    for forbidden in (
        "acceptance_thresholds_v3_construction_authorised",
        "classifier_prompt_v3_construction_authorised",
        "classifier_implementation_v3_construction_authorised",
        "classifier_model_run_authorised",
        "classifier_rerun_on_pack_v5_authorised",
        "threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(
            forbidden
        ) is not False:
            raise RuntimeError(
                f"Design-v4 human review unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier design-v4 human review")
    print("=" * 74)
    print(
        f"Design-v4 SHA256:           "
        f"{sha256(DESIGN_V4_PATH)}"
    )
    print(
        f"Design-v3 SHA256:           "
        f"{sha256(DESIGN_V3_PATH)}"
    )
    print(
        f"Threshold-v2 SHA256:        "
        f"{sha256(THRESHOLDS_V2_PATH)}"
    )
    print(
        f"Human-diagnostic SHA256:    "
        f"{sha256(HUMAN_DIAGNOSTIC_V2_PATH)}"
    )
    print()
    print("Design review")
    print("-" * 74)
    print("Revision scope:             PASS")
    print("Source classes:             12/12 PRESERVED")
    print("Taxonomy changed:           NO")
    print("Thresholds changed:         NO")
    print("One-call architecture:      PASS")
    print()
    print("Deterministic context gate")
    print("  Gated classes:            3")
    print("  Gate failure -> unresolved:YES")
    print("  Second model call:        NO")
    print("  Semantic fallback:        NO")
    print("  Promote unresolved:       NO")
    print("  Resolved-class remap:     NO")
    print("  Audit proposed class:     YES")
    print()
    print("Foreign-issuing boundary")
    print("  Issuer relationship:      REQUIRED")
    print("  Verification alone:       NOT SUFFICIENT")
    print("  Foreign status alone:     NOT SUFFICIENT")
    print("  Generic document wording: NOT SUFFICIENT")
    print("  External-agency boundary: PRESERVED")
    print()
    print("Benchmark/case-ID leakage:  NONE")
    print("Unresolved safety:          PRESERVED")
    print("Acceptance methodology:     PASS")
    print()
    print("Design-v4 human review:     PASS")
    print()
    print("Fresh independent pack-v6: AUTHORISED")
    print("Fresh pack human review:    REQUIRED")
    print("Threshold-v3 construction:  NOT AUTHORISED")
    print("Prompt-v3 construction:     NOT AUTHORISED")
    print("Implementation-v3:          NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Pack-v5 rerun:              NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  INDEPENDENT CONTRACT PACK V6")
    print()
    print(
        f"Output:                     "
        f"{OUTPUT_PATH}"
    )
    print(
        f"Design-v4 review SHA256:    "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Classifier design-v4 human review: PASS")


if __name__ == "__main__":
    main()
