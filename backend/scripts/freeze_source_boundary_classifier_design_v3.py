"""Freeze Waypoint source-boundary classifier design v3.

DESIGN ONLY.
- No model calls.
- No classifier implementation.
- No prompt changes.
- No production changes.
- No rerun of the observed contract pack.

This design responds to the frozen human diagnostic review while remaining
generic and benchmark-independent.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_design_v3.py
    uv run python -m scripts.freeze_source_boundary_classifier_design_v3

Output:
    tests/source_boundary_classifier_design_v3.json
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
HUMAN_DIAGNOSTIC_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_human_diagnostic_review_v1.json"
)
SCORE_RESULT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_score_result_v1.json"
)
OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
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
EXPECTED_HUMAN_DIAGNOSTIC_SHA256 = (
    "C81FA04D71A1AE91CFF4959E8F70105E"
    "CBE08C267C01E9048C3DBB2967AC9AA5"
)
EXPECTED_SCORE_RESULT_SHA256 = (
    "CFEEC8CAD5009FACA2FA6AAA10FC7E88D"
    "CA490DCC0AD11AA3CFF4E40334ECE17"
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
        "responsible_authority_type": "new_zealand_legislature_or_regulator",
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
        "responsible_authority_type": "professional_or_assessment_authority",
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
            "Refusing to freeze classifier design v3."
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
            f"Classifier design v3 already exists: {OUTPUT_PATH}\n"
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
        HUMAN_DIAGNOSTIC_PATH,
        EXPECTED_HUMAN_DIAGNOSTIC_SHA256,
        "Frozen human diagnostic review v1",
    )
    require_sha(
        SCORE_RESULT_PATH,
        EXPECTED_SCORE_RESULT_SHA256,
        "Frozen first acceptance-result",
    )

    diagnostic = load_json(HUMAN_DIAGNOSTIC_PATH)
    score_result = load_json(SCORE_RESULT_PATH)

    if diagnostic.get("schema") != (
        "waypoint-source-boundary-classifier-human-diagnostic-review-v1"
    ):
        raise RuntimeError(
            "Unexpected human diagnostic review schema."
        )

    if diagnostic.get("status") != (
        "FROZEN_DIAGNOSIS_REVISED_CLASSIFIER_DESIGN_V3_AUTHORISED"
    ):
        raise RuntimeError(
            "Human diagnostic review does not authorise design v3."
        )

    if diagnostic.get(
        "authorisations",
        {},
    ).get("classifier_design_v3_authorised") is not True:
        raise RuntimeError(
            "Classifier design v3 is not authorised."
        )

    if score_result.get("status") != (
        "FROZEN_FIRST_UNTOUCHED_ACCEPTANCE_FAIL"
    ):
        raise RuntimeError(
            "Design v3 must remain bound to the frozen failed first run."
        )

    if set(DETERMINISTIC_DERIVATION) != set(SOURCE_CLASSES):
        raise RuntimeError(
            "Deterministic derivation does not cover every source class."
        )

    if len(SOURCE_CLASSES) != 12:
        raise RuntimeError(
            "Frozen source-class taxonomy must contain 12 classes."
        )

    design = {
        "schema": (
            "waypoint-source-boundary-classifier-design-v3"
        ),
        "status": (
            "FROZEN_REVISED_DESIGN_READY_FOR_INDEPENDENT_PACK_CONSTRUCTION"
        ),
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "authoritative_source_boundary_v1_sha256": (
                EXPECTED_BOUNDARY_SHA256
            ),
            "classifier_design_v2_sha256": (
                EXPECTED_DESIGN_V2_SHA256
            ),
            "human_diagnostic_review_v1_sha256": (
                EXPECTED_HUMAN_DIAGNOSTIC_SHA256
            ),
            "first_acceptance_result_v1_sha256": (
                EXPECTED_SCORE_RESULT_SHA256
            ),
        },
        "purpose": (
            "Classify the authoritative source home of one unsupported "
            "proposition. The classifier does not decide whether retrieved "
            "Manual evidence is sufficient and does not answer the user's "
            "question."
        ),
        "inputs": {
            "required": [
                "unsupported_proposition",
            ],
            "optional": [
                "trusted_source_context",
            ],
            "forbidden": [
                "test_id",
                "expected_label",
                "expected_output",
                "gold",
                "contrast_group",
                "acceptance_thresholds",
                "retrieved_manual_chunks",
                "original_user_question",
                "retired_benchmark_data",
            ],
        },
        "model_output_contract": {
            "independent_fields_only": True,
            "fields": {
                "source_class": {
                    "type": "enum",
                    "allowed_values": SOURCE_CLASSES,
                    "required": True,
                },
                "basis": {
                    "type": "string",
                    "required": True,
                    "role": "diagnostic_only_not_scored",
                },
            },
            "model_must_not_generate": [
                "resolution_status",
                "source_domain",
                "responsible_authority_type",
            ],
            "rationale": (
                "resolution_status, source_domain, and "
                "responsible_authority_type are deterministic functions of "
                "source_class. Removing dependent categorical generation "
                "eliminates invalid cross-field combinations by construction."
            ),
        },
        "deterministic_derivation": (
            DETERMINISTIC_DERIVATION
        ),
        "semantic_resolution_policy": {
            "principle": (
                "Use proposition semantics when those semantics identify the "
                "authoritative source role. Trusted source context is not a "
                "universal prerequisite."
            ),
            "semantically_resolvable_without_trusted_context": {
                "operational_manual_instruction": (
                    "A proposition about an immigration eligibility criterion, "
                    "exception, requirement, condition, obligation, or other "
                    "certified instruction rule."
                ),
                "legislation_or_regulation": (
                    "A proposition about statutory, regulatory, or other legal "
                    "authority rather than operational instruction content."
                ),
                "inz_live_service_information": (
                    "A proposition about a current or time-varying INZ service "
                    "state or operational value, such as current processing "
                    "timeframes, submission-channel availability, service "
                    "opening state, or capped-place availability."
                ),
                "current_fee_or_charge_information": (
                    "A proposition asking for the current payable amount of an "
                    "immigration fee, levy, charge, or location-dependent "
                    "application cost."
                ),
                "foreign_issuing_authority_procedure": (
                    "A proposition about obtaining, replacing, issuing, "
                    "certifying, or verifying a document or record from the "
                    "foreign authority responsible for issuing that item."
                ),
                "external_agency_assessment_or_service": (
                    "A proposition about an assessment, recognition, or "
                    "administrative service owned by a non-professional "
                    "external official agency."
                ),
                "external_entitlement_or_service_regime": (
                    "A proposition about eligibility for, access to, or rules "
                    "of a separately administered public benefit or public "
                    "service regime outside immigration instructions."
                ),
                "professional_or_assessor_guidance": (
                    "A proposition whose authoritative home belongs to a "
                    "professional, clinical, registration, provider, or "
                    "specialist assessor role."
                ),
            },
        },
        "trusted_context_gates": {
            "principle": (
                "Trusted context is mandatory only where proposition semantics "
                "cannot establish a specific publication/source family."
            ),
            "manual_instruction_transition": {
                "context_required": True,
                "required_context": {
                    "publisher_family": "immigration_new_zealand",
                    "publication_family": "certified_amendment",
                    "certification_status": "certified",
                    "incorporation_status": [
                        "not_yet_indexed",
                        "stale_local_index",
                    ],
                },
            },
            "inz_non_manual_procedure_or_interpretation": {
                "context_required": True,
                "required_context": {
                    "publisher_family": "immigration_new_zealand",
                    "publication_family": [
                        "inz_iac",
                        "inz_advice_to_staff",
                        "inz_form_or_guide",
                    ],
                },
                "rule": (
                    "Procedural semantics alone do not prove that the "
                    "authoritative home is a specific INZ non-Manual "
                    "publication family."
                ),
            },
            "other_official_external_authority": {
                "context_required": True,
                "required_context": {
                    "publisher_family": "other_official_authority",
                    "authority_role": "other_official_operational_owner",
                },
                "rule": (
                    "This is a context-gated last-resort resolved class. Use it "
                    "only after all more specific source classes are excluded."
                ),
            },
        },
        "class_boundaries_and_precedence": [
            {
                "priority": 1,
                "rule": (
                    "Professional, clinical, registration, provider, and "
                    "specialist-assessor ownership takes precedence over "
                    "generic external-agency assessment/service ownership."
                ),
            },
            {
                "priority": 2,
                "rule": (
                    "A current payable fee, levy, or charge amount is "
                    "current_fee_or_charge_information; the legal authority "
                    "that creates or permits the charge is "
                    "legislation_or_regulation."
                ),
            },
            {
                "priority": 3,
                "rule": (
                    "A current INZ service state or operational value is "
                    "inz_live_service_information; a certified eligibility or "
                    "instruction rule is operational_manual_instruction."
                ),
            },
            {
                "priority": 4,
                "rule": (
                    "foreign_issuing_authority_procedure requires an issuing "
                    "role. A foreign customs, border, traveller-declaration, "
                    "benefit, tax, policing, or other general operational "
                    "process is not an issuing-authority procedure merely "
                    "because the responsible authority is foreign."
                ),
            },
            {
                "priority": 5,
                "rule": (
                    "other_official_external_authority is used only when "
                    "trusted context establishes a generic official "
                    "operational owner and no specific external class applies."
                ),
            },
        ],
        "unresolved_policy": {
            "use_when": [
                (
                    "The proposition does not semantically identify a source "
                    "role strongly enough to choose one frozen source class."
                ),
                (
                    "A context-gated class is plausible but its required "
                    "trusted source context is absent or insufficient."
                ),
                (
                    "Two or more source classes remain materially plausible "
                    "after applying the frozen precedence rules."
                ),
            ],
            "do_not_use_when": (
                "The proposition semantics themselves identify one of the "
                "classes explicitly designated as semantically resolvable "
                "without trusted context."
            ),
            "safety_goal": (
                "Preserve conservative unresolved behaviour for genuinely "
                "ambiguous ownership without turning absence of metadata into "
                "a universal abstention trigger."
            ),
        },
        "validation_contract": {
            "strict_json_object": True,
            "extra_fields_forbidden": True,
            "source_class_enum_enforced": True,
            "basis_string_required": True,
            "dependent_fields_derived_not_validated_from_model": True,
            "malformed_json_is_error": True,
            "invalid_source_class_is_error": True,
            "automatic_retry": False,
            "repair_call": False,
            "fallback_model": False,
            "do_not_relax_validation_to_improve_score": True,
        },
        "prompt_contract": {
            "zero_shot": True,
            "examples": False,
            "benchmark_literals": False,
            "synthetic_test_ids": False,
            "manual_section_literals": False,
            "question_specific_branches": False,
            "section_specific_boosts": False,
            "expected_answer_mappings": False,
            "instructions": [
                (
                    "Classify only the exact unsupported proposition supplied "
                    "to the classifier."
                ),
                "Do not answer the proposition.",
                "Do not provide immigration advice.",
                (
                    "Do not decide whether retrieved Manual evidence is "
                    "sufficient."
                ),
                (
                    "Apply proposition semantics first for classes explicitly "
                    "designated as semantically resolvable."
                ),
                (
                    "Apply trusted-context gates only to the classes whose "
                    "design explicitly requires context."
                ),
                (
                    "Return unresolved when ownership remains genuinely "
                    "ambiguous after applying class boundaries and precedence."
                ),
                (
                    "Return exactly source_class and basis."
                ),
            ],
        },
        "evaluation_methodology": {
            "observed_contract_pack_v3": (
                "DEVELOPMENT_AND_REGRESSION_ONLY"
            ),
            "observed_contract_pack_v3_may_be_used_for_regression": True,
            "observed_contract_pack_v3_must_not_support_new_untouched_acceptance_claim": True,
            "new_independent_acceptance_pack_required": True,
            "new_pack_must_be_written_without_copying_observed_case_wording": True,
            "new_pack_must_cover_all_12_source_classes": True,
            "new_pack_must_include_semantic_vs_context_gate_contrasts": True,
            "new_pack_must_include_foreign_issuing_vs_other_official_contrasts": True,
            "new_pack_must_include_current_fee_vs_legal_basis_contrasts": True,
            "new_pack_must_include_live_service_vs_instruction_contrasts": True,
            "new_pack_must_include_unresolved_safety_cases": True,
            "acceptance_thresholds_must_be_frozen_before_prediction": True,
            "acceptance_thresholds_must_not_be_weaker_than_prior_percentage_and_safety_floors": True,
            "automatic_retry_for_acceptance_run": False,
            "manual_override": False,
        },
        "non_goals": [
            "Answer generation",
            "Manual retrieval",
            "External-source retrieval",
            "Production runtime integration",
            "Candidate v7 construction",
            "Benchmark optimisation",
        ],
        "authorisations": {
            "classifier_design_v3_frozen": True,
            "new_independent_acceptance_pack_construction_authorised": True,
            "classifier_implementation_v2_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_model_run_authorised": False,
            "observed_pack_rerun_as_untouched_authorised": False,
            "acceptance_threshold_change_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_independent_contract_pack_v4"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Construct a new independent synthetic acceptance pack against "
                "the frozen design v3, without reusing observed contract-pack "
                "propositions or case-specific tuning."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            design,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_REVISED_DESIGN_READY_FOR_INDEPENDENT_PACK_CONSTRUCTION"
    ):
        raise RuntimeError(
            "Saved classifier design v3 status changed."
        )

    if saved.get(
        "model_output_contract",
        {},
    ).get("independent_fields_only") is not True:
        raise RuntimeError(
            "Design v3 no longer uses independent model output only."
        )

    saved_classes = saved.get(
        "model_output_contract",
        {},
    ).get("fields", {}).get(
        "source_class",
        {},
    ).get("allowed_values")

    if saved_classes != SOURCE_CLASSES:
        raise RuntimeError(
            "Saved source-class taxonomy changed."
        )

    saved_derivation = saved.get("deterministic_derivation")

    if saved_derivation != DETERMINISTIC_DERIVATION:
        raise RuntimeError(
            "Saved deterministic derivation changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get(
        "new_independent_acceptance_pack_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Independent acceptance-pack construction was not authorised."
        )

    for forbidden in (
        "classifier_implementation_v2_authorised",
        "classifier_prompt_change_authorised",
        "classifier_model_run_authorised",
        "observed_pack_rerun_as_untouched_authorised",
        "acceptance_threshold_change_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_source_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Design v3 unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier design v3 freeze")
    print("=" * 63)
    print(
        f"Human diagnostic SHA256:   "
        f"{sha256(HUMAN_DIAGNOSTIC_PATH)}"
    )
    print(
        f"Prior design v2 SHA256:     "
        f"{sha256(DESIGN_V2_PATH)}"
    )
    print()
    print("Core architecture")
    print("-" * 63)
    print("Model categorical output:   source_class ONLY")
    print("Diagnostic output:          basis")
    print("resolution_status:          DERIVED")
    print("source_domain:              DERIVED")
    print("authority_type:             DERIVED")
    print("Source classes:             12")
    print()
    print("Context policy")
    print("-" * 63)
    print("Universal context gate:     REMOVED")
    print("Semantic resolution:        EXPLICIT")
    print("Transition context gate:    PRESERVED")
    print("INZ non-Manual gate:        PRESERVED")
    print("Other-official gate:        PRESERVED")
    print()
    print("Foreign issuing boundary:   NARROWED TO ISSUING ROLE")
    print("Unresolved safety:          PRESERVED")
    print("Automatic retry:            NO")
    print("Repair call:                NO")
    print()
    print("Design v3:                  FROZEN")
    print("New independent pack:       AUTHORISED")
    print("Implementation:             NOT AUTHORISED")
    print("Prompt change:              NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Observed-pack rerun:        NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  INDEPENDENT CONTRACT PACK V4")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Design-v3 SHA256:           {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Classifier design v3 freeze: PASS")


if __name__ == "__main__":
    main()
