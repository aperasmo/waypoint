"""Freeze Waypoint source-boundary classifier design v4.

DESIGN SPECIFICATION ONLY.
- No model calls.
- No prompt changes.
- No classifier implementation changes.
- No threshold changes.
- No production changes.
- Preserves the 12-class taxonomy.
- Adds only the two generic revisions authorised by human diagnostic review v2:
    1) deterministic enforcement of existing context gates;
    2) a narrower foreign-issuing verification boundary.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_design_v4.py
    uv run python -m scripts.freeze_source_boundary_classifier_design_v4

Output:
    tests/source_boundary_classifier_design_v4.json
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

FAILURE_ANALYSIS_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_failure_analysis_v2.json"
)

HUMAN_REVIEW_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_human_diagnostic_review_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v4.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
)

EXPECTED_THRESHOLDS_V2_SHA256 = (
    "1BDD2ED8950D6E3E612C66DCD5384BD5"
    "E0CAC784E39A70C3CE09EAD5C310D277"
)

EXPECTED_FAILURE_ANALYSIS_V2_SHA256 = (
    "DA353315AB3EB4CB409064BD850B42893"
    "F6D59590077BA4550152EC463294F06"
)

EXPECTED_HUMAN_REVIEW_V2_SHA256 = (
    "B981E258FEB7EFB26B2901386522366B2"
    "30C82465D81A459DC91B1162E503392"
)


SOURCE_CLASSES = [
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


DETERMINISTIC_DERIVATION = {
    "operational_manual_instruction": {
        "resolution_status": "resolved",
        "source_domain": "certified_immigration_instructions",
        "responsible_authority_type": "immigration_new_zealand",
    },
    "manual_instruction_transition": {
        "resolution_status": "resolved",
        "source_domain": "certified_immigration_instructions",
        "responsible_authority_type": "immigration_new_zealand",
    },
    "legislation_or_regulation": {
        "resolution_status": "resolved",
        "source_domain": "legislation_or_regulation",
        "responsible_authority_type": (
            "new_zealand_legislature_or_regulator"
        ),
    },
    "inz_live_service_information": {
        "resolution_status": "resolved",
        "source_domain": "official_inz_non_manual",
        "responsible_authority_type": "immigration_new_zealand",
    },
    "current_fee_or_charge_information": {
        "resolution_status": "resolved",
        "source_domain": "official_inz_non_manual",
        "responsible_authority_type": "immigration_new_zealand",
    },
    "inz_non_manual_procedure_or_interpretation": {
        "resolution_status": "resolved",
        "source_domain": "official_inz_non_manual",
        "responsible_authority_type": "immigration_new_zealand",
    },
    "foreign_issuing_authority_procedure": {
        "resolution_status": "resolved",
        "source_domain": "responsible_external_official_authority",
        "responsible_authority_type": "foreign_issuing_authority",
    },
    "external_agency_assessment_or_service": {
        "resolution_status": "resolved",
        "source_domain": "responsible_external_official_authority",
        "responsible_authority_type": "external_government_agency",
    },
    "external_entitlement_or_service_regime": {
        "resolution_status": "resolved",
        "source_domain": "responsible_external_official_authority",
        "responsible_authority_type": "public_service_authority",
    },
    "professional_or_assessor_guidance": {
        "resolution_status": "resolved",
        "source_domain": "responsible_external_official_authority",
        "responsible_authority_type": (
            "professional_or_assessment_authority"
        ),
    },
    "other_official_external_authority": {
        "resolution_status": "resolved",
        "source_domain": "responsible_external_official_authority",
        "responsible_authority_type": "other_official_authority",
    },
    "unresolved": {
        "resolution_status": "unresolved",
        "source_domain": "unresolved",
        "responsible_authority_type": "unresolved",
    },
}


CONTEXT_GATES = {
    "manual_instruction_transition": {
        "required": {
            "publisher_family": "immigration_new_zealand",
            "publication_family": "certified_amendment",
            "certification_status": "certified",
        },
        "allowed": {
            "incorporation_status": [
                "not_yet_indexed",
                "stale_local_index",
            ],
        },
        "on_gate_failure": "unresolved",
    },
    "inz_non_manual_procedure_or_interpretation": {
        "required": {
            "publisher_family": "immigration_new_zealand",
        },
        "allowed": {
            "publication_family": [
                "inz_iac",
                "inz_advice_to_staff",
                "inz_form_or_guide",
            ],
        },
        "on_gate_failure": "unresolved",
    },
    "other_official_external_authority": {
        "required": {
            "publisher_family": "other_official_authority",
            "authority_role": "other_official_operational_owner",
        },
        "allowed": {},
        "on_gate_failure": "unresolved",
    },
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
            "Refusing design-v4 freeze."
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
            f"Design-v4 artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    for path, expected, label in (
        (
            RUNTIME_PATH,
            EXPECTED_RUNTIME_SHA256,
            "Frozen production candidate-v2 runtime",
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
            FAILURE_ANALYSIS_V2_PATH,
            EXPECTED_FAILURE_ANALYSIS_V2_SHA256,
            "Frozen failure analysis v2",
        ),
        (
            HUMAN_REVIEW_V2_PATH,
            EXPECTED_HUMAN_REVIEW_V2_SHA256,
            "Frozen human diagnostic review v2",
        ),
    ):
        require_sha(
            path,
            expected,
            label,
        )

    design_v3 = load_json(
        DESIGN_V3_PATH
    )
    thresholds_v2 = load_json(
        THRESHOLDS_V2_PATH
    )
    failure_analysis = load_json(
        FAILURE_ANALYSIS_V2_PATH
    )
    human_review = load_json(
        HUMAN_REVIEW_V2_PATH
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

    if failure_analysis.get("status") != (
        "FROZEN_DIAGNOSTIC_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Failure analysis is not frozen for design review."
        )

    if human_review.get("schema") != (
        "waypoint-source-boundary-classifier-human-diagnostic-review-v2"
    ):
        raise RuntimeError(
            "Unexpected human-review schema."
        )

    if human_review.get("status") != (
        "APPROVED_DESIGN_V4_CONSTRUCTION_ONLY"
    ):
        raise RuntimeError(
            "Human review does not authorise design-v4 construction."
        )

    if human_review.get(
        "authorisations",
        {},
    ).get(
        "classifier_design_v4_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Design-v4 construction is not authorised."
        )

    # Preserve the 12-class taxonomy exactly.
    if len(SOURCE_CLASSES) != 12:
        raise RuntimeError(
            "Design-v4 taxonomy must contain exactly 12 source classes."
        )

    if len(set(SOURCE_CLASSES)) != 12:
        raise RuntimeError(
            "Design-v4 taxonomy contains duplicate source classes."
        )

    if set(DETERMINISTIC_DERIVATION) != set(SOURCE_CLASSES):
        raise RuntimeError(
            "Deterministic derivation does not cover all 12 source classes."
        )

    if set(CONTEXT_GATES) != {
        "manual_instruction_transition",
        "inz_non_manual_procedure_or_interpretation",
        "other_official_external_authority",
    }:
        raise RuntimeError(
            "Design-v4 context-gated class set changed."
        )

    artifact = {
        "schema": (
            "waypoint-source-boundary-classifier-design-v4"
        ),
        "status": (
            "FROZEN_DESIGN_READY_FOR_HUMAN_REVIEW"
        ),
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
            ),
            "acceptance_thresholds_v2_sha256": (
                EXPECTED_THRESHOLDS_V2_SHA256
            ),
            "failure_analysis_v2_sha256": (
                EXPECTED_FAILURE_ANALYSIS_V2_SHA256
            ),
            "human_diagnostic_review_v2_sha256": (
                EXPECTED_HUMAN_REVIEW_V2_SHA256
            ),
        },
        "revision_scope": {
            "taxonomy_changed": False,
            "source_class_count": 12,
            "thresholds_changed": False,
            "model_changed": False,
            "one_model_call_changed": False,
            "retry_policy_changed": False,
            "repair_policy_changed": False,
            "fallback_policy_changed": False,
            "required_changes": [
                "DETERMINISTIC_CONTEXT_GATE_ENFORCEMENT",
                "FOREIGN_ISSUING_VERIFICATION_BOUNDARY",
            ],
        },
        "classifier_architecture": {
            "stage_1_model_proposal": {
                "model_generated_fields": [
                    "proposed_source_class",
                    "basis",
                ],
                "proposed_source_class_allowed_values": (
                    SOURCE_CLASSES
                ),
                "zero_shot": True,
                "model_calls": 1,
                "automatic_retry": False,
                "repair_call": False,
                "fallback_model": False,
            },
            "stage_2_deterministic_validation": {
                "model_calls": 0,
                "input_fields": [
                    "proposed_source_class",
                    "trusted_source_context",
                ],
                "output_field": (
                    "source_class"
                ),
                "purpose": (
                    "Enforce only the frozen context gates. "
                    "No semantic reclassification is performed here."
                ),
                "may_demote_to_unresolved": True,
                "may_promote_unresolved_to_resolved": False,
                "may_remap_one_resolved_class_to_another": False,
            },
            "stage_3_deterministic_derivation": {
                "input_field": "source_class",
                "derived_fields": [
                    "resolution_status",
                    "source_domain",
                    "responsible_authority_type",
                ],
                "mapping": (
                    DETERMINISTIC_DERIVATION
                ),
            },
            "diagnostic_fields": {
                "preserve_proposed_source_class": True,
                "preserve_basis": True,
                "record_gate_action": True,
                "gate_action_values": [
                    "not_applicable",
                    "passed",
                    "failed_to_unresolved",
                ],
            },
        },
        "source_classes": {
            "allowed_values": (
                SOURCE_CLASSES
            ),
            "count": 12,
            "definitions": {
                "operational_manual_instruction": (
                    "A substantive certified immigration-instruction rule, "
                    "including an eligibility criterion, condition, exception, "
                    "requirement, obligation, permission, or restriction whose "
                    "authoritative home is certified immigration instructions."
                ),
                "manual_instruction_transition": (
                    "A certified immigration-instruction amendment that is "
                    "authoritative but is not yet represented correctly in the "
                    "local Operational Manual index. This class is context-gated."
                ),
                "legislation_or_regulation": (
                    "A statutory, regulatory, or other legal-authority "
                    "proposition concerning legal basis, power, obligation, or "
                    "authority itself."
                ),
                "inz_live_service_information": (
                    "A current or time-varying Immigration New Zealand service "
                    "state or operational value, such as current timeframe, "
                    "availability, channel state, quota, or appointment state."
                ),
                "current_fee_or_charge_information": (
                    "The current payable amount of an immigration fee, levy, "
                    "charge, surcharge, or location/channel-dependent "
                    "application cost."
                ),
                "inz_non_manual_procedure_or_interpretation": (
                    "An Immigration New Zealand non-Manual procedural or "
                    "interpretive publication. This class is context-gated."
                ),
                "foreign_issuing_authority_procedure": (
                    "A procedure owned by a foreign authority acting in an "
                    "established issuing role for the relevant document or "
                    "official record."
                ),
                "external_agency_assessment_or_service": (
                    "An assessment, recognition, verification, or administrative "
                    "service owned by a non-professional external official agency "
                    "when a more specific source-owner class does not apply."
                ),
                "external_entitlement_or_service_regime": (
                    "Eligibility for, access to, or rules of a separately "
                    "administered public benefit or public service regime outside "
                    "immigration instructions."
                ),
                "professional_or_assessor_guidance": (
                    "Guidance or requirements owned by a professional, clinical, "
                    "registration, provider, or specialist-assessor role."
                ),
                "other_official_external_authority": (
                    "A generic official external operational owner when no more "
                    "specific external class applies. This is a context-gated "
                    "last-resort resolved class."
                ),
                "unresolved": (
                    "The authoritative source home cannot be resolved safely "
                    "because material ambiguity remains or a required context "
                    "gate is not satisfied."
                ),
            },
        },
        "context_gate_policy": {
            "universal_context_gate": False,
            "gated_classes": (
                CONTEXT_GATES
            ),
            "deterministic_enforcement": {
                "required": True,
                "timing": (
                    "after model proposal and before deterministic "
                    "domain/authority derivation"
                ),
                "rule": (
                    "If proposed_source_class is context-gated and all required "
                    "trusted-context conditions are not satisfied, final "
                    "source_class MUST be unresolved."
                ),
                "no_second_model_call": True,
                "no_semantic_fallback": True,
                "no_alternate_resolved_class_selection": True,
                "audit_proposed_class": True,
            },
            "non_gated_classes": {
                "semantic_resolution_without_trusted_context_allowed": [
                    "operational_manual_instruction",
                    "legislation_or_regulation",
                    "inz_live_service_information",
                    "current_fee_or_charge_information",
                    "foreign_issuing_authority_procedure",
                    "external_agency_assessment_or_service",
                    "external_entitlement_or_service_regime",
                    "professional_or_assessor_guidance",
                ],
                "unresolved_is_always_allowed": True,
            },
        },
        "foreign_issuing_boundary": {
            "rule": (
                "The foreign-issuing class requires an established issuing "
                "relationship for the relevant document or official record."
            ),
            "issuer_relationship_may_be_established_by": [
                "clear proposition semantics",
                "trusted source context",
            ],
            "issuing_role_actions_may_include": [
                "issue",
                "replace",
                "certify",
                "verify",
            ],
            "verification_specific_rule": (
                "Verification of an already-issued document does not by itself "
                "establish that the authority is the issuer of that document or "
                "is acting in an issuing capacity. Verification qualifies for "
                "foreign_issuing_authority_procedure only when issuer identity "
                "or issuing role for the relevant document/record is also "
                "established."
            ),
            "external_agency_boundary": (
                "When the proposition clearly establishes a government-agency "
                "verification, recognition, assessment, or administrative "
                "service but does not establish issuer identity/role, classify "
                "external_agency_assessment_or_service unless another more "
                "specific class applies."
            ),
            "ambiguity_rule": (
                "If neither an issuing role nor a distinct external-agency "
                "service role can be resolved safely, use unresolved."
            ),
            "must_not_infer_issuer_from": [
                "verification alone",
                "the fact that an authority is foreign",
                "generic public-records or document-related wording alone",
            ],
        },
        "precedence_and_boundaries": {
            "professional_precedence": (
                "Professional, clinical, registration, provider, or specialist-"
                "assessor ownership takes precedence over a generic external-"
                "agency assessment/service classification."
            ),
            "fee_vs_legal_basis": (
                "A current payable immigration fee/levy/charge amount is "
                "current_fee_or_charge_information. The legal authority creating "
                "or authorising it is legislation_or_regulation."
            ),
            "live_service_vs_instruction": (
                "A current INZ service state/value is "
                "inz_live_service_information. A substantive certified "
                "immigration criterion, condition, exception, or rule is "
                "operational_manual_instruction."
            ),
            "other_official_last_resort": (
                "other_official_external_authority is used only when no more "
                "specific external class applies and its trusted context gate "
                "passes."
            ),
        },
        "unresolved_policy": {
            "preserve_conservative_safety": True,
            "use_when": [
                (
                    "two or more source classes remain materially plausible "
                    "after precedence rules"
                ),
                (
                    "a proposed context-gated class fails its deterministic "
                    "trusted-context gate"
                ),
                (
                    "source-owner role remains materially unspecified"
                ),
            ],
            "do_not_use_merely_because": [
                (
                    "trusted metadata is absent for a non-gated class whose "
                    "source role is clear from proposition semantics"
                ),
            ],
        },
        "output_contract": {
            "model_output": {
                "fields": {
                    "proposed_source_class": {
                        "type": "enum",
                        "allowed_values": (
                            SOURCE_CLASSES
                        ),
                    },
                    "basis": {
                        "type": "string",
                        "diagnostic_only": True,
                    },
                },
                "extra_fields_forbidden": True,
            },
            "final_classifier_output": {
                "fields": [
                    "proposed_source_class",
                    "source_class",
                    "resolution_status",
                    "source_domain",
                    "responsible_authority_type",
                    "basis",
                    "gate_action",
                ],
                "source_class_is_post_validation": True,
                "dependent_fields_derive_from": (
                    "source_class"
                ),
            },
        },
        "implementation_constraints": {
            "no_examples_in_prompt": True,
            "no_test_ids": True,
            "no_benchmark_literals": True,
            "no_expected_answer_mappings": True,
            "no_question_specific_branches": True,
            "no_section_specific_logic": True,
            "no_threshold_specific_prediction_logic": True,
            "no_eval_artifact_reads_in_classifier": True,
            "one_model_call": True,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "deterministic_gate_must_be_unit_testable_without_model_call": True,
        },
        "acceptance_methodology": {
            "pack_v5_status": (
                "DEVELOPMENT_DIAGNOSTIC_ONLY"
            ),
            "pack_v5_may_not_be_reused_as_fresh_acceptance": True,
            "same_prediction_set_may_not_be_rerun_for_acceptance": True,
            "fresh_independent_acceptance_pack_required": True,
            "fresh_pack_must_be_constructed_after_design_v4_human_review": True,
            "fresh_pack_must_not_copy_old_case_literals": True,
            "acceptance_thresholds_must_be_frozen_before_new_predictions": True,
            "all_gates_required": True,
            "manual_override": False,
        },
        "change_control": {
            "design_v4_is_specification_only": True,
            "classifier_v2_remains_unchanged": True,
            "production_runtime_remains_unchanged": True,
            "acceptance_thresholds_v2_remain_unchanged": True,
        },
        "authorisations": {
            "design_v4_human_review_authorised": True,
            "fresh_independent_acceptance_pack_construction_authorised": False,
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
                "source_boundary_classifier_design_v4_human_review"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Review design v4 for faithful implementation of the two "
                "authorised generic revisions, taxonomy preservation, "
                "deterministic gate semantics, and absence of benchmark-"
                "specific logic before authorising a new independent pack."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            artifact,
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
        "FROZEN_DESIGN_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Saved design-v4 status changed."
        )

    if saved.get(
        "revision_scope",
        {},
    ).get(
        "source_class_count"
    ) != 12:
        raise RuntimeError(
            "Saved design-v4 class count changed."
        )

    if saved.get(
        "revision_scope",
        {},
    ).get(
        "taxonomy_changed"
    ) is not False:
        raise RuntimeError(
            "Saved design-v4 unexpectedly changes taxonomy."
        )

    saved_architecture = saved.get(
        "classifier_architecture",
        {},
    )

    if saved_architecture.get(
        "stage_2_deterministic_validation",
        {},
    ).get(
        "may_demote_to_unresolved"
    ) is not True:
        raise RuntimeError(
            "Saved design-v4 does not preserve deterministic demotion."
        )

    if saved_architecture.get(
        "stage_2_deterministic_validation",
        {},
    ).get(
        "may_remap_one_resolved_class_to_another"
    ) is not False:
        raise RuntimeError(
            "Saved design-v4 unexpectedly permits resolved-class remapping."
        )

    saved_auth = saved.get(
        "authorisations",
        {},
    )

    if saved_auth.get(
        "design_v4_human_review_authorised"
    ) is not True:
        raise RuntimeError(
            "Design-v4 human review was not authorised."
        )

    for forbidden in (
        "fresh_independent_acceptance_pack_construction_authorised",
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
                f"Design-v4 unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier design v4")
    print("=" * 72)
    print(
        f"Design-v3 SHA256:           "
        f"{sha256(DESIGN_V3_PATH)}"
    )
    print(
        f"Threshold-v2 SHA256:        "
        f"{sha256(THRESHOLDS_V2_PATH)}"
    )
    print(
        f"Failure-analysis SHA256:    "
        f"{sha256(FAILURE_ANALYSIS_V2_PATH)}"
    )
    print(
        f"Human-review SHA256:        "
        f"{sha256(HUMAN_REVIEW_V2_PATH)}"
    )
    print()
    print("Revision scope")
    print("-" * 72)
    print("Source classes:             12")
    print("Taxonomy changed:           NO")
    print("Thresholds changed:         NO")
    print("Model changed:              NO")
    print("One-call architecture:      PRESERVED")
    print()
    print("Revision 1")
    print("  DETERMINISTIC CONTEXT-GATE ENFORCEMENT")
    print("  Context-gated classes:    3")
    print("  Failed gate final class:  unresolved")
    print("  Second model call:        NO")
    print("  Promote unresolved:       NO")
    print("  Resolved-class remap:     NO")
    print()
    print("Revision 2")
    print("  FOREIGN-ISSUING VERIFICATION BOUNDARY")
    print("  Verification alone:       NOT SUFFICIENT")
    print("  Issuer role required:     YES")
    print("  Generic agency service:   external_agency_assessment_or_service")
    print()
    print("Model proposal field:       proposed_source_class")
    print("Final validated field:      source_class")
    print("Dependent fields derive:    source_class")
    print()
    print("Pack-v5 future role:        DEVELOPMENT/DIAGNOSTIC ONLY")
    print("Fresh acceptance pack:      REQUIRED")
    print()
    print("Design-v4 human review:     AUTHORISED")
    print("Fresh pack construction:    NOT AUTHORISED")
    print("Prompt construction:        NOT AUTHORISED")
    print("Implementation construction:NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Pack-v5 rerun:              NOT AUTHORISED")
    print("Threshold change:           NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  DESIGN-V4 HUMAN REVIEW")
    print()
    print(
        f"Output:                     "
        f"{OUTPUT_PATH}"
    )
    print(
        f"Design-v4 SHA256:           "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Classifier design v4 freeze: PASS")


if __name__ == "__main__":
    main()
