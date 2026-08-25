"""Freeze Waypoint source-boundary classifier design v2.

This revises design v1 only for the human-reviewed ambiguities HR1-HR4.
It does not modify runtime and does not authorise a classifier model run.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_design_v2.py
    uv run python -m scripts.freeze_source_boundary_classifier_design_v2

Output:
    tests/source_boundary_classifier_design_v2.json
"""

from __future__ import annotations

import hashlib
import json
import re
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

DESIGN_V1_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v1.json"
)

HUMAN_REVIEW_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_contract_pack_human_review_v1.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v2.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_BOUNDARY_SHA256 = (
    "2BFC518CFD892FE54AD9E46EAEE0037A9"
    "05730DDA934E3EEAEB1EBAD42C1458F"
)

EXPECTED_DESIGN_V1_SHA256 = (
    "9443153C67A690EC24177BE61AA28CAB5"
    "E4794A90A171E44F3FAB4216A05F69F"
)

EXPECTED_HUMAN_REVIEW_SHA256 = (
    "12302B8CEBBBE36FC5C1338A586954A96"
    "1B0BDC691A03954C28FDD0B2AF89BE2"
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
            "Refusing to freeze classifier design v2."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Classifier design v2 already exists: {OUTPUT_PATH}\n"
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
        DESIGN_V1_PATH,
        EXPECTED_DESIGN_V1_SHA256,
        "Frozen classifier design v1",
    )
    require_sha(
        HUMAN_REVIEW_PATH,
        EXPECTED_HUMAN_REVIEW_SHA256,
        "Frozen contract-pack human review",
    )

    boundary = load_json(BOUNDARY_PATH)
    design_v1 = load_json(DESIGN_V1_PATH)
    review = load_json(HUMAN_REVIEW_PATH)

    if boundary.get("schema") != (
        "waypoint-authoritative-source-boundary-spec-v1"
    ):
        raise RuntimeError("Unexpected source-boundary schema.")

    if design_v1.get("schema") != (
        "waypoint-source-boundary-classifier-design-v1"
    ):
        raise RuntimeError("Unexpected classifier design-v1 schema.")

    if review.get("schema") != (
        "waypoint-source-boundary-contract-pack-human-review-v1"
    ):
        raise RuntimeError("Unexpected human-review schema.")

    if review.get("status") != (
        "REVIEWED_REVISE_BEFORE_IMPLEMENTATION"
    ):
        raise RuntimeError("Unexpected human-review status.")

    if review.get("review_decision", {}).get(
        "classifier_design_v1"
    ) != "REVISE_FOR_DISAMBIGUATION":
        raise RuntimeError(
            "Human review does not authorise classifier design-v2."
        )

    if review.get("next_engineering_task", {}).get(
        "name"
    ) != "source_boundary_classifier_design_v2":
        raise RuntimeError(
            "Unexpected human-review next engineering task."
        )

    if review.get("next_engineering_task", {}).get(
        "runtime_implementation_authorised"
    ) is not False:
        raise RuntimeError(
            "Human review unexpectedly authorises runtime implementation."
        )

    design = {
        "schema": "waypoint-source-boundary-classifier-design-v2",
        "status": "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE",
        "frozen_on": str(date.today()),
        "purpose": (
            "Resolve the authoritative source domain of one exact material "
            "proposition that an upstream support decision has already "
            "identified as unsupported by supplied Operational Manual "
            "evidence."
        ),
        "revision_basis": {
            "design_v1_sha256": EXPECTED_DESIGN_V1_SHA256,
            "human_review_sha256": EXPECTED_HUMAN_REVIEW_SHA256,
            "blocking_findings_addressed": [
                "HR1",
                "HR2",
                "HR3",
                "HR4",
            ],
            "top_level_source_boundary_changed": False,
            "public_evidence_status_mapping_changed": False,
        },
        "baseline": {
            "production_candidate": "evidence_adequacy_v2",
            "runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
        },
        "preconditions": [
            (
                "The upstream process has already determined that supplied "
                "Operational Manual evidence is insufficient for one material "
                "proposition."
            ),
            (
                "The unsupported proposition is stated neutrally and does "
                "not contain a guessed answer or guessed source class."
            ),
            (
                "The classifier does not determine whether the user's whole "
                "question is answerable."
            ),
            (
                "Source-location-only classifications may require trusted "
                "source context. Where required context is absent, the "
                "classifier must return unresolved."
            ),
        ],
        "classifier_input": {
            "unsupported_proposition": {
                "type": "string",
                "required": True,
                "description": (
                    "The exact material proposition whose authoritative "
                    "ownership must be resolved."
                ),
            },
            "trusted_source_context": {
                "type": "object | null",
                "required": False,
                "description": (
                    "Optional structured metadata supplied by a separate "
                    "trusted source registry or verified source transition. "
                    "It must never contain evaluation labels, benchmark IDs, "
                    "expected sections, model answers, or adjudication notes."
                ),
                "allowed_fields": {
                    "publisher_family": [
                        "immigration_new_zealand",
                        "new_zealand_legislation",
                        "foreign_official_authority",
                        "new_zealand_external_agency",
                        "public_service_authority",
                        "professional_or_assessment_authority",
                        "other_official_authority",
                    ],
                    "publication_family": [
                        "operational_manual",
                        "certified_amendment",
                        "primary_legislation",
                        "secondary_legislation",
                        "inz_iac",
                        "inz_advice_to_staff",
                        "inz_form_or_guide",
                        "inz_live_service",
                        "inz_fee_service",
                        "foreign_issuing_service",
                        "external_agency_service",
                        "public_entitlement_regime",
                        "professional_or_assessment_service",
                        "other_official_service",
                    ],
                    "authority_role": [
                        "immigration_instruction_owner",
                        "legislative_authority",
                        "document_issuing_authority",
                        "non_professional_agency_assessment",
                        "public_entitlement_owner",
                        "professional_registration",
                        "clinical_assessment",
                        "professional_assessment",
                        "other_official_operational_owner",
                    ],
                    "certification_status": [
                        "certified",
                        "not_applicable",
                    ],
                    "incorporation_status": [
                        "incorporated",
                        "not_yet_indexed",
                        "stale_local_index",
                        "not_applicable",
                    ],
                },
                "forbidden_fields": [
                    "gold_status",
                    "expected_section",
                    "benchmark_identifier",
                    "question_identifier",
                    "adjudication_result",
                    "expected_answer",
                ],
            },
        },
        "classifier_output": {
            "resolution_status": [
                "resolved",
                "unresolved",
            ],
            "source_domain": [
                "certified_immigration_instructions",
                "legislation_or_regulation",
                "official_inz_non_manual",
                "responsible_external_official_authority",
                "unresolved",
            ],
            "source_class": [
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
            ],
            "responsible_authority_type": [
                "immigration_new_zealand",
                "new_zealand_legislation",
                "foreign_issuing_authority",
                "new_zealand_external_agency",
                "public_service_authority",
                "professional_or_assessment_authority",
                "other_official_authority",
                "unresolved",
            ],
            "basis": (
                "A concise explanation of why the proposition belongs to the "
                "selected source class. It must not answer the proposition."
            ),
        },
        "source_class_precedence": [
            {
                "order": 1,
                "source_class": "manual_instruction_transition",
                "condition": (
                    "Trusted source context identifies a certified "
                    "immigration amendment that is not yet incorporated in "
                    "the local indexed Manual or the local index is stale."
                ),
            },
            {
                "order": 2,
                "source_class": "legislation_or_regulation",
                "condition": (
                    "The proposition itself concerns statutory authority, a "
                    "legal rule, or a requirement prescribed by legislation "
                    "or regulation."
                ),
            },
            {
                "order": 3,
                "source_class": "operational_manual_instruction",
                "condition": (
                    "The proposition itself is an immigration rule, criterion, "
                    "condition, evidence requirement, exception, definition, "
                    "consequence, verification rule, assessment rule, or "
                    "decision criterion."
                ),
            },
            {
                "order": 4,
                "source_class": "inz_live_service_information",
                "condition": (
                    "The proposition asks for a current or time-varying INZ "
                    "service state or value other than a current fee/charge."
                ),
            },
            {
                "order": 5,
                "source_class": "current_fee_or_charge_information",
                "condition": (
                    "The proposition asks for the current payable fee, levy, "
                    "or charge amount, rather than the legal authority for "
                    "imposing it."
                ),
            },
            {
                "order": 6,
                "source_class": "inz_non_manual_procedure_or_interpretation",
                "condition": (
                    "Trusted source context explicitly identifies an official "
                    "INZ non-Manual publication family such as an IAC, Advice "
                    "to Staff, or official form/guide."
                ),
            },
            {
                "order": 7,
                "source_class": "foreign_issuing_authority_procedure",
                "condition": (
                    "The proposition concerns a foreign official authority's "
                    "own document-issuing or application procedure."
                ),
            },
            {
                "order": 8,
                "source_class": "professional_or_assessor_guidance",
                "condition": (
                    "The responsible authority is professional, clinical, "
                    "registration, provider, or assessor-specific and owns "
                    "the proposition within that professional or assessment "
                    "remit."
                ),
            },
            {
                "order": 9,
                "source_class": "external_agency_assessment_or_service",
                "condition": (
                    "The proposition concerns a non-professional government "
                    "or statutory agency's assessment, recognition, or "
                    "service process."
                ),
            },
            {
                "order": 10,
                "source_class": "external_entitlement_or_service_regime",
                "condition": (
                    "The proposition concerns eligibility for a separately "
                    "administered public service, benefit, or entitlement "
                    "regime."
                ),
            },
            {
                "order": 11,
                "source_class": "other_official_external_authority",
                "condition": (
                    "Trusted source context identifies an official external "
                    "operational owner, and every more specific frozen class "
                    "has been excluded."
                ),
            },
        ],
        "source_class_contracts": [
            {
                "source_class": "operational_manual_instruction",
                "source_domain": "certified_immigration_instructions",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "The proposition is itself an immigration rule, visa "
                    "criterion, visa condition, immigration evidence "
                    "requirement, exception, immigration definition, "
                    "immigration consequence, verification rule, assessment "
                    "rule, or decision criterion."
                ),
                "trusted_source_context_required": False,
                "future_status_mapping_if_support_already_insufficient": (
                    "corpus_gap"
                ),
            },
            {
                "source_class": "manual_instruction_transition",
                "source_domain": "certified_immigration_instructions",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "Trusted source context establishes a certified "
                    "immigration-instruction amendment that is pending local "
                    "incorporation/indexing or is newer than the local index."
                ),
                "trusted_source_context_required": True,
                "required_context": {
                    "publisher_family": "immigration_new_zealand",
                    "publication_family": "certified_amendment",
                    "certification_status": "certified",
                },
                "exclusions": [
                    (
                        "Do not infer this class from future dates, recency "
                        "wording, or absence from retrieved Manual passages."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "corpus_gap"
                ),
            },
            {
                "source_class": "legislation_or_regulation",
                "source_domain": "legislation_or_regulation",
                "responsible_authority_type": "new_zealand_legislation",
                "use_when": (
                    "The proposition itself concerns legal authority, a "
                    "statutory rule, or a requirement prescribed by "
                    "legislation/regulation."
                ),
                "trusted_source_context_required": False,
                "exclusions": [
                    (
                        "Do not use this class merely because an immigration "
                        "instruction ultimately derives authority from law."
                    ),
                    (
                        "A current fee amount belongs to the current-fee class; "
                        "the legal authority for charging it belongs here."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "inz_live_service_information",
                "source_domain": "official_inz_non_manual",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "The proposition is a current/time-varying INZ service "
                    "state such as processing time, application status, "
                    "availability, location, or channel state."
                ),
                "trusted_source_context_required": False,
                "exclusions": [
                    "Current fees and charges use the dedicated fee class.",
                    (
                        "Static immigration eligibility rules do not become "
                        "live service information merely because they may "
                        "change over time."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "current_fee_or_charge_information",
                "source_domain": "official_inz_non_manual",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "The proposition asks for a current payable amount, fee, "
                    "levy, charge, or current fee-waiver result."
                ),
                "trusted_source_context_required": False,
                "exclusions": [
                    (
                        "The legal basis for imposing a fee or levy belongs to "
                        "legislation/regulation."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "inz_non_manual_procedure_or_interpretation",
                "source_domain": "official_inz_non_manual",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "Trusted source context identifies an official INZ "
                    "non-Manual publication or source family that owns the "
                    "administrative procedure, interpretation, or form-specific "
                    "handling proposition."
                ),
                "trusted_source_context_required": True,
                "required_publication_families_any_of": [
                    "inz_iac",
                    "inz_advice_to_staff",
                    "inz_form_or_guide",
                ],
                "exclusions": [
                    (
                        "Procedural wording alone is insufficient because "
                        "some procedures may be stated in certified "
                        "instructions."
                    ),
                    (
                        "Without trusted non-Manual source-location context, "
                        "return unresolved rather than infer this class."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "foreign_issuing_authority_procedure",
                "source_domain": "responsible_external_official_authority",
                "responsible_authority_type": "foreign_issuing_authority",
                "use_when": (
                    "The proposition concerns how a foreign official authority "
                    "issues, requests, verifies, or requires an application "
                    "for its own official document."
                ),
                "trusted_source_context_required": False,
                "exclusions": [
                    (
                        "An INZ requirement to provide that foreign document "
                        "is an immigration-instruction proposition, not an "
                        "issuing-authority procedure."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "professional_or_assessor_guidance",
                "source_domain": "responsible_external_official_authority",
                "responsible_authority_type": (
                    "professional_or_assessment_authority"
                ),
                "use_when": (
                    "The proposition concerns a professional, clinical, "
                    "registration, provider-specific, or assessor-specific "
                    "requirement or procedure."
                ),
                "trusted_source_context_required": False,
                "positive_authority_roles": [
                    "professional_registration",
                    "clinical_assessment",
                    "professional_assessment",
                ],
                "exclusions": [
                    (
                        "Non-professional statutory/government agency "
                        "recognition or assessment services belong to "
                        "external_agency_assessment_or_service."
                    ),
                ],
                "precedence_over": [
                    "external_agency_assessment_or_service",
                    "other_official_external_authority",
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "external_agency_assessment_or_service",
                "source_domain": "responsible_external_official_authority",
                "responsible_authority_type": "new_zealand_external_agency",
                "use_when": (
                    "The proposition concerns a non-professional New Zealand "
                    "government/statutory agency's assessment, recognition, "
                    "or service process."
                ),
                "trusted_source_context_required": False,
                "positive_authority_roles": [
                    "non_professional_agency_assessment",
                ],
                "exclusions": [
                    (
                        "Professional registration, clinical assessment, "
                        "provider-specific assessment, and professional "
                        "assessment belong to "
                        "professional_or_assessor_guidance."
                    ),
                    (
                        "Public-service entitlement eligibility belongs to "
                        "external_entitlement_or_service_regime."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "external_entitlement_or_service_regime",
                "source_domain": "responsible_external_official_authority",
                "responsible_authority_type": "public_service_authority",
                "use_when": (
                    "The proposition concerns eligibility for, or entitlement "
                    "to, a separately administered public service, benefit, "
                    "or statutory service regime."
                ),
                "trusted_source_context_required": False,
                "exclusions": [
                    (
                        "An immigration condition that indirectly affects "
                        "eligibility remains an immigration-instruction "
                        "proposition; the entitlement decision itself belongs "
                        "here."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "other_official_external_authority",
                "source_domain": "responsible_external_official_authority",
                "responsible_authority_type": "other_official_authority",
                "use_when": (
                    "Trusted source context identifies an official authority "
                    "that operationally owns the proposition, and no more "
                    "specific frozen class applies."
                ),
                "trusted_source_context_required": True,
                "required_context": {
                    "publisher_family": "other_official_authority",
                    "authority_role": "other_official_operational_owner",
                },
                "exclusions": [
                    "Do not use as a catch-all for uncertainty.",
                    (
                        "Do not use where the proposition fits foreign "
                        "issuing procedure, agency assessment, public "
                        "entitlement, professional/assessor guidance, "
                        "legislation/regulation, or an INZ class."
                    ),
                    (
                        "If a more specific class cannot be excluded, return "
                        "unresolved."
                    ),
                ],
                "future_status_mapping_if_support_already_insufficient": (
                    "external_source_required"
                ),
            },
        ],
        "resolution_algorithm": [
            {
                "step": 1,
                "rule": (
                    "Classify the exact unsupported proposition, not the "
                    "broad visa, occupation, nationality, or application "
                    "topic."
                ),
            },
            {
                "step": 2,
                "rule": (
                    "If trusted context establishes a certified immigration "
                    "amendment transition, resolve to "
                    "manual_instruction_transition."
                ),
            },
            {
                "step": 3,
                "rule": (
                    "Otherwise determine whether the proposition itself is "
                    "legal/regulatory or an immigration instruction. Do not "
                    "confuse legal authority with instruction content."
                ),
            },
            {
                "step": 4,
                "rule": (
                    "For current/time-varying INZ service values, separate "
                    "current fees/charges from other live-service information."
                ),
            },
            {
                "step": 5,
                "rule": (
                    "Resolve INZ non-Manual procedure/interpretation only when "
                    "trusted source context explicitly identifies a non-Manual "
                    "publication family. Otherwise return unresolved."
                ),
            },
            {
                "step": 6,
                "rule": (
                    "For external authorities, first resolve foreign issuing "
                    "procedures, then professional/clinical/registration "
                    "authorities, then non-professional agency assessment "
                    "services, then public entitlement regimes."
                ),
            },
            {
                "step": 7,
                "rule": (
                    "Use other_official_external_authority only with trusted "
                    "context identifying an official operational owner after "
                    "all more specific classes are excluded."
                ),
            },
            {
                "step": 8,
                "rule": (
                    "If authoritative ownership or class exclusivity cannot "
                    "be established without guessing, return unresolved."
                ),
            },
        ],
        "consistency_invariants": [
            (
                "resolution_status=unresolved requires source_domain="
                "unresolved, source_class=unresolved, and "
                "responsible_authority_type=unresolved."
            ),
            (
                "resolution_status=resolved prohibits any unresolved field."
            ),
            (
                "manual_instruction_transition requires trusted source "
                "context identifying a certified amendment."
            ),
            (
                "inz_non_manual_procedure_or_interpretation requires trusted "
                "source context identifying an INZ non-Manual publication."
            ),
            (
                "other_official_external_authority requires trusted source "
                "context identifying an official operational owner."
            ),
            (
                "professional_or_assessor_guidance takes precedence over "
                "external_agency_assessment_or_service when the authority "
                "role is professional, clinical, registration, or "
                "professional assessment."
            ),
            (
                "external_agency_assessment_or_service excludes professional, "
                "clinical, registration, and public-entitlement authority "
                "roles."
            ),
            (
                "A current payable fee/levy amount and the legal authority "
                "for imposing that charge are different proposition types and "
                "must not share a source class merely because they concern "
                "the same charge."
            ),
        ],
        "classifier_must_not": [
            "Answer the unsupported proposition.",
            "Generate immigration advice.",
            "Determine whether retrieved evidence is sufficient.",
            "Determine decision_boundary.",
            "Choose public evidence_status directly.",
            "Read evaluation or gold files.",
            "Use benchmark IDs or expected-section mappings.",
            "Use question-specific routing.",
            "Use visa-category-to-source mappings.",
            "Use section-code-specific routing.",
            "Use nationality-specific routing.",
            "Use occupation-specific routing.",
            "Use unrestricted web search.",
            "Infer source location from retrieval silence.",
            (
                "Infer an INZ non-Manual publication solely from procedural "
                "wording."
            ),
            (
                "Use other_official_external_authority as a catch-all for "
                "ambiguous ownership."
            ),
            "Silently default unresolved authority to corpus_gap.",
            (
                "Silently default unresolved authority to "
                "external_source_required."
            ),
        ],
        "future_deterministic_mapping": {
            "implemented": False,
            "mappings": [
                {
                    "source_class": "operational_manual_instruction",
                    "evidence_status_if_support_already_insufficient": (
                        "corpus_gap"
                    ),
                },
                {
                    "source_class": "manual_instruction_transition",
                    "evidence_status_if_support_already_insufficient": (
                        "corpus_gap"
                    ),
                },
                {
                    "source_domain": "legislation_or_regulation",
                    "evidence_status_if_support_already_insufficient": (
                        "external_source_required"
                    ),
                },
                {
                    "source_domain": "official_inz_non_manual",
                    "evidence_status_if_support_already_insufficient": (
                        "external_source_required"
                    ),
                },
                {
                    "source_domain": (
                        "responsible_external_official_authority"
                    ),
                    "evidence_status_if_support_already_insufficient": (
                        "external_source_required"
                    ),
                },
                {
                    "source_domain": "unresolved",
                    "behaviour": (
                        "Explicit unresolved authority. Do not fabricate a "
                        "public evidence_status."
                    ),
                },
            ],
        },
        "evaluation_reporting_contract": {
            "freeze_status": "FROZEN_BEFORE_ANY_CLASSIFIER_MODEL_RUN",
            "primary_case_metric": {
                "name": "four_field_exact_match_accuracy",
                "fields": [
                    "resolution_status",
                    "source_domain",
                    "source_class",
                    "responsible_authority_type",
                ],
            },
            "required_secondary_metrics": [
                "resolution_status_accuracy",
                "source_domain_accuracy",
                "source_class_accuracy",
                "source_class_macro_recall",
                "per_source_class_recall",
                "unresolved_recall",
                "resolved_recall",
                "contrast_group_full_consistency_rate",
                "malformed_or_error_rate",
            ],
            "confusion_outputs": [
                "resolution_status_confusion",
                "source_domain_confusion",
                "source_class_confusion",
            ],
            "error_treatment": {
                "malformed_output": "incorrect",
                "classifier_error": "incorrect",
                "automatic_retry": False,
                "unresolved_expected_case": (
                    "Correct only when all frozen unresolved output fields "
                    "are returned as unresolved."
                ),
            },
            "acceptance_thresholds_frozen": False,
            "reason_thresholds_not_yet_frozen": (
                "A revised independent contract test pack v2 must first be "
                "human-reviewed and frozen. Acceptance thresholds must then "
                "be frozen before the first classifier model prediction."
            ),
        },
        "required_contract_test_pack_v2_changes": [
            {
                "addresses": "HR1",
                "requirement": (
                    "INZ non-Manual resolved tests must include trusted source "
                    "context identifying the non-Manual publication family. "
                    "Semantically similar cases without that context must "
                    "expect unresolved."
                ),
            },
            {
                "addresses": "HR2",
                "requirement": (
                    "Include contrast pairs separating non-professional agency "
                    "assessment from professional/clinical/registration "
                    "authority procedure."
                ),
            },
            {
                "addresses": "HR3",
                "requirement": (
                    "Replace ambiguous other-official examples with cases "
                    "that include trusted source context and clearly exclude "
                    "every more specific source class. Include an ambiguous "
                    "counterpart that expects unresolved."
                ),
            },
            {
                "addresses": "HR4",
                "requirement": (
                    "The future scorer must report every metric frozen in "
                    "evaluation_reporting_contract. Do not alter expected "
                    "labels after any model output is observed."
                ),
            },
        ],
        "authorisations": {
            "classifier_design_v2_frozen": True,
            "contract_test_pack_v2_build_authorised": True,
            "classifier_model_prediction_authorised": False,
            "classifier_experimental_implementation_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_step": {
            "name": "source_boundary_classifier_contract_test_pack_v2",
            "authorised": True,
            "runtime_implementation_authorised": False,
            "model_prediction_authorised": False,
            "purpose": (
                "Build a new independent synthetic contract test pack against "
                "design v2, then human-review and freeze it before setting "
                "classifier acceptance thresholds."
            ),
        },
        "immutability": {
            "design_v1_remains_frozen_history": True,
            "human_review_v1_remains_frozen_history": True,
            "do_not_overwrite_prior_artifacts": True,
        },
    }

    serialised = json.dumps(
        design,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    forbidden_keys = (
        "expected_sections",
        "candidate_id",
        "case_id",
        "adjudication_note",
        "benchmark_status",
    )

    for key in forbidden_keys:
        if re.search(
            rf'"{re.escape(key)}"\s*:',
            serialised,
            flags=re.IGNORECASE,
        ):
            raise RuntimeError(
                f"Forbidden benchmark/evaluation field in design v2: {key}"
            )

    benchmark_ids = sorted(
        set(
            re.findall(
                r"\bext2?_[0-9a-f]{16}\b",
                serialised,
                flags=re.IGNORECASE,
            )
        )
    )

    if benchmark_ids:
        raise RuntimeError(
            "Forbidden benchmark IDs in design v2: "
            f"{benchmark_ids}"
        )

    section_literals = sorted(
        set(
            re.findall(
                r'"((?:A|R|SR|U|V|WA|WD)\d+(?:\.\d+)*)"',
                serialised,
            )
        )
    )

    if section_literals:
        raise RuntimeError(
            "Hard-coded Operational Manual section literals found: "
            f"{section_literals}"
        )

    OUTPUT_PATH.write_text(
        serialised,
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError(
            "Saved classifier design-v2 status verification failed."
        )

    authorisations = saved.get("authorisations", {})

    if authorisations.get(
        "contract_test_pack_v2_build_authorised"
    ) is not True:
        raise RuntimeError(
            "Design v2 does not authorise contract test-pack v2."
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
        if authorisations.get(forbidden_authorisation) is not False:
            raise RuntimeError(
                "Design v2 unexpectedly authorises: "
                f"{forbidden_authorisation}"
            )

    reporting = saved.get("evaluation_reporting_contract", {})

    if reporting.get("freeze_status") != (
        "FROZEN_BEFORE_ANY_CLASSIFIER_MODEL_RUN"
    ):
        raise RuntimeError(
            "Evaluation reporting contract is not frozen."
        )

    if reporting.get("acceptance_thresholds_frozen") is not False:
        raise RuntimeError(
            "Acceptance thresholds should not yet be frozen."
        )

    print("Waypoint source-boundary classifier design-v2 freeze")
    print("=" * 53)
    print(f"Production v2 SHA256:       {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:       {sha256(BOUNDARY_PATH)}")
    print(f"Classifier design v1:       {sha256(DESIGN_V1_PATH)}")
    print(f"Human review v1:            {sha256(HUMAN_REVIEW_PATH)}")
    print()
    print("Human-review blockers addressed")
    print("-" * 53)
    print("HR1  INZ non-Manual requires trusted source context")
    print("HR2  Agency vs professional classes now exclusive")
    print("HR3  Other-official is context-gated last resort")
    print("HR4  Evaluation reporting metrics frozen")
    print()
    print("Top-level source domains:    UNCHANGED")
    print("Public status mapping:       UNCHANGED")
    print("Unresolved outcome:          PRESERVED")
    print()
    print("Context-gated classes")
    print("-" * 53)
    print("manual_instruction_transition")
    print("inz_non_manual_procedure_or_interpretation")
    print("other_official_external_authority")
    print()
    print("External precedence")
    print("-" * 53)
    print("foreign issuing procedure")
    print("professional / clinical / registration")
    print("non-professional agency assessment/service")
    print("public entitlement/service regime")
    print("other official authority, only after exclusions")
    print()
    print("Evaluation reporting frozen")
    print("-" * 53)
    print("4-field exact match")
    print("resolution-status accuracy")
    print("source-domain accuracy")
    print("source-class accuracy")
    print("source-class macro recall")
    print("per-class recall")
    print("resolved / unresolved recall")
    print("contrast-group consistency")
    print("malformed/error rate")
    print()
    print("Acceptance thresholds:      NOT YET FROZEN")
    print("Classifier model prediction:NOT AUTHORISED")
    print("Classifier implementation:  NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  CONTRACT TEST PACK V2")
    print("Test-pack v2 build:         AUTHORISED")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Classifier design-v2 SHA:   {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Source-boundary classifier design-v2 freeze: PASS")


if __name__ == "__main__":
    main()
