"""Freeze fresh independent contract test pack v6 for Waypoint classifier.

CONSTRUCTION ONLY.
- No model calls.
- Built from frozen classifier design v4 and its human review.
- Does NOT read pack v5.
- Does NOT read old predictions, scores, or failure-analysis artifacts.
- Contains no prior case IDs.
- Must be human-reviewed before thresholds or implementation are authorised.

Pack structure:
- 50 total cases.
- 4 fresh cases for each of 11 resolved source classes = 44.
- 6 unresolved cases.
- 14 contrast groups.
- All three context-gated classes exercised.
- Foreign-issuing vs external-agency boundary exercised.
- Semantic non-gated resolution without trusted context exercised.
- Conservative unresolved ambiguity exercised.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_independent_pack_v6.py
    uv run python -m scripts.freeze_source_boundary_classifier_independent_pack_v6

Output:
    tests/source_boundary_classifier_independent_contract_test_pack_v6.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
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

DESIGN_V4_REVIEW_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v4_human_review.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v6.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_DESIGN_V4_SHA256 = (
    "9563158E74CFBC0C7D25D2DC2BA8FC20"
    "36E0B32193BADDFBE464ECCB99329948"
)

EXPECTED_DESIGN_V4_REVIEW_SHA256 = (
    "4456BEE89A249043510730BF5A01FCE05"
    "EF0A6C49EDF39FAD2EBBB55E17D9AD5"
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

DERIVATION = {
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


def expected(source_class: str) -> dict[str, str]:
    derived = DERIVATION[source_class]
    return {
        "resolution_status": derived["resolution_status"],
        "source_domain": derived["source_domain"],
        "source_class": source_class,
        "responsible_authority_type": derived[
            "responsible_authority_type"
        ],
    }


def case(
    case_id: str,
    proposition: str,
    source_class: str,
    basis: str,
    *,
    context: dict[str, str] | None = None,
    contrast_group: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "unsupported_proposition": proposition,
        "trusted_source_context": context,
        "expected": expected(source_class),
        "basis": basis,
        "contrast_group": contrast_group,
    }


CASES = [
    # operational_manual_instruction: 4
    case(
        "v6_001",
        "Whether a worker visa holder must obtain approval before moving to an employer not covered by the conditions of the current visa.",
        "operational_manual_instruction",
        "This is a substantive immigration condition and permission rule governing a visa holder's ability to change employment.",
        contrast_group="instruction_condition_vs_live_service",
    ),
    case(
        "v6_002",
        "What minimum maintenance funds an applicant must demonstrate to satisfy the financial requirement for a student visa category.",
        "operational_manual_instruction",
        "This is an instruction-defined eligibility requirement about financial evidence, not a current service value or fee.",
        contrast_group="instruction_requirement_vs_statutory_power",
    ),
    case(
        "v6_003",
        "Whether an applicant can qualify under an instruction-defined exception when the normal sponsorship requirement is not met.",
        "operational_manual_instruction",
        "This is a substantive exception within certified immigration instructions.",
        contrast_group="instruction_exception_vs_nonmanual_process",
    ),
    case(
        "v6_004",
        "What maximum period of stay certified immigration instructions permit for applicants granted a particular temporary visa category.",
        "operational_manual_instruction",
        "This is a substantive immigration rule specifying the permitted duration under a visa category.",
        contrast_group="instruction_rule_vs_external_entitlement",
    ),

    # manual_instruction_transition: 4
    case(
        "v6_005",
        "Whether a newly certified amendment changing the qualifying employment period is authoritative even though the local instruction index has not yet incorporated it.",
        "manual_instruction_transition",
        "Trusted context establishes a certified INZ amendment that is authoritative and not yet indexed locally.",
        context={
            "publisher_family": "immigration_new_zealand",
            "publication_family": "certified_amendment",
            "certification_status": "certified",
            "incorporation_status": "not_yet_indexed",
        },
        contrast_group="certified_transition_vs_uncertain_change",
    ),
    case(
        "v6_006",
        "Which partner eligibility rule applies after a certified immigration amendment when the local instruction index still shows the superseded wording.",
        "manual_instruction_transition",
        "Trusted context establishes a certified amendment with a stale local index.",
        context={
            "publisher_family": "immigration_new_zealand",
            "publication_family": "certified_amendment",
            "certification_status": "certified",
            "incorporation_status": "stale_local_index",
        },
    ),
    case(
        "v6_007",
        "Whether a certified amendment replacing the evidence requirement for a residence pathway governs applications before the local manual index is updated.",
        "manual_instruction_transition",
        "The authoritative source is a certified amendment not yet incorporated into the local index.",
        context={
            "publisher_family": "immigration_new_zealand",
            "publication_family": "certified_amendment",
            "certification_status": "certified",
            "incorporation_status": "not_yet_indexed",
        },
    ),
    case(
        "v6_008",
        "Which certified immigration rule applies when an amendment has taken effect but the locally indexed instruction text remains stale.",
        "manual_instruction_transition",
        "Trusted metadata establishes a certified INZ amendment and stale local instruction index.",
        context={
            "publisher_family": "immigration_new_zealand",
            "publication_family": "certified_amendment",
            "certification_status": "certified",
            "incorporation_status": "stale_local_index",
        },
    ),

    # legislation_or_regulation: 4
    case(
        "v6_009",
        "Which statutory provision gives immigration officers the legal power to require specified information from a person at the border.",
        "legislation_or_regulation",
        "The proposition asks for the legal authority conferring a statutory power.",
        contrast_group="instruction_requirement_vs_statutory_power",
    ),
    case(
        "v6_010",
        "Whether regulations legally authorise the government to impose an immigration-related levy on a prescribed application.",
        "legislation_or_regulation",
        "This asks about the legal basis for imposing a levy, not its current payable amount.",
        contrast_group="legal_levy_basis_vs_current_levy_amount",
    ),
    case(
        "v6_011",
        "Which enactment authorises immigration information to be disclosed to another public authority for a specified statutory purpose.",
        "legislation_or_regulation",
        "The source home is legislation because the proposition concerns statutory authority for information sharing.",
    ),
    case(
        "v6_012",
        "What legal provision creates an immigration officer's power to cancel a visa in prescribed circumstances.",
        "legislation_or_regulation",
        "This is a legal-power proposition whose authoritative home is legislation or regulation.",
    ),

    # inz_live_service_information: 4
    case(
        "v6_013",
        "What processing timeframe Immigration New Zealand currently publishes for most applications in a particular visa category.",
        "inz_live_service_information",
        "A currently published processing timeframe is a time-varying INZ service value.",
        contrast_group="instruction_condition_vs_live_service",
    ),
    case(
        "v6_014",
        "Whether Immigration New Zealand's online application channel is currently accepting new submissions for a specified service.",
        "inz_live_service_information",
        "Current submission-channel availability is live INZ service information.",
        contrast_group="live_service_vs_current_fee",
    ),
    case(
        "v6_015",
        "How many appointment times are currently available through an Immigration New Zealand booking service for the coming week.",
        "inz_live_service_information",
        "Current appointment availability is a live operational service state.",
    ),
    case(
        "v6_016",
        "Whether places remain available today in an Immigration New Zealand service with a currently administered numerical cap.",
        "inz_live_service_information",
        "Current remaining capacity in a capped INZ service is a time-varying operational value.",
    ),

    # current_fee_or_charge_information: 4
    case(
        "v6_017",
        "What application fee Immigration New Zealand currently charges for a specified visa application lodged from New Zealand.",
        "current_fee_or_charge_information",
        "The proposition asks for the current payable immigration application amount.",
        contrast_group="live_service_vs_current_fee",
    ),
    case(
        "v6_018",
        "What immigration levy amount is currently included in the amount payable for a specified residence application.",
        "current_fee_or_charge_information",
        "This asks for the current payable levy value rather than the legal authority creating the levy.",
        contrast_group="legal_levy_basis_vs_current_levy_amount",
    ),
    case(
        "v6_019",
        "What additional service charge Immigration New Zealand currently applies when an applicant chooses a specified application channel.",
        "current_fee_or_charge_information",
        "A current channel-dependent charge is current fee or charge information.",
        contrast_group="current_value_vs_ambiguous_amount",
    ),
    case(
        "v6_020",
        "What current payable surcharge applies to an Immigration New Zealand application lodged from a specified location.",
        "current_fee_or_charge_information",
        "The proposition asks for a current location-dependent immigration charge.",
    ),

    # inz_non_manual_procedure_or_interpretation: 4
    case(
        "v6_021",
        "What processing steps an Immigration New Zealand internal administration circular directs staff to follow when triaging a specified application type.",
        "inz_non_manual_procedure_or_interpretation",
        "Trusted context identifies an INZ internal administration circular, a non-Manual procedural publication.",
        context={
            "publisher_family": "immigration_new_zealand",
            "publication_family": "inz_iac",
        },
        contrast_group="instruction_exception_vs_nonmanual_process",
    ),
    case(
        "v6_022",
        "How an Immigration New Zealand Advice to Staff publication tells officers to handle a specified transitional processing situation.",
        "inz_non_manual_procedure_or_interpretation",
        "Trusted context identifies an INZ Advice to Staff procedural publication.",
        context={
            "publisher_family": "immigration_new_zealand",
            "publication_family": "inz_advice_to_staff",
        },
    ),
    case(
        "v6_023",
        "Which file-format and upload instructions an Immigration New Zealand application guide gives applicants for supporting photographs.",
        "inz_non_manual_procedure_or_interpretation",
        "Trusted context identifies an INZ form or guide containing procedural instructions.",
        context={
            "publisher_family": "immigration_new_zealand",
            "publication_family": "inz_form_or_guide",
        },
        contrast_group="nonmanual_with_context_vs_ambiguous_guidance",
    ),
    case(
        "v6_024",
        "Where an Immigration New Zealand form guide tells applicants to provide a sponsor's supporting documents in the online process.",
        "inz_non_manual_procedure_or_interpretation",
        "Trusted context identifies a non-Manual INZ form or guide.",
        context={
            "publisher_family": "immigration_new_zealand",
            "publication_family": "inz_form_or_guide",
        },
    ),

    # foreign_issuing_authority_procedure: 4
    case(
        "v6_025",
        "How the national civil registry that issued a person's marriage certificate allows that person to obtain an official replacement certificate.",
        "foreign_issuing_authority_procedure",
        "The proposition explicitly establishes the civil registry as issuer of the record and asks about replacement in that issuing role.",
        contrast_group="foreign_issuer_replacement_vs_generic_foreign_operation",
    ),
    case(
        "v6_026",
        "How the foreign police records authority that issues national police clearance certificates allows an applicant to request a new certificate.",
        "foreign_issuing_authority_procedure",
        "The issuing relationship is explicit: the authority issues the police clearance record being requested.",
        contrast_group="issuing_role_vs_ambiguous_document_check",
    ),
    case(
        "v6_027",
        "What process the foreign passport authority that issued a traveller's passport requires to replace that passport after serious damage.",
        "foreign_issuing_authority_procedure",
        "The proposition clearly establishes the passport authority's issuing role for the relevant document.",
    ),
    case(
        "v6_028",
        "How a national civil registry verifies the authenticity of a birth record that the same registry issued.",
        "foreign_issuing_authority_procedure",
        "Verification is within the foreign-issuing class here because the proposition explicitly establishes that the verifying registry is also the issuer of the relevant record.",
        contrast_group="issuer_verified_record_vs_independent_verification_service",
    ),

    # external_agency_assessment_or_service: 4
    case(
        "v6_029",
        "Which assessment service a government qualifications agency provides to compare an overseas secondary-school qualification with the domestic framework.",
        "external_agency_assessment_or_service",
        "This is an assessment service owned by an external government agency, not immigration instructions or a professional-assessor role.",
        contrast_group="government_assessment_vs_professional_assessment",
    ),
    case(
        "v6_030",
        "Which identity-checking service a government identity agency provides to confirm that a person's digital identity matches official records.",
        "external_agency_assessment_or_service",
        "This is a government agency verification service rather than a document-issuing procedure.",
    ),
    case(
        "v6_031",
        "Which authentication service a national archives agency offers for documents originating from several public bodies, where the archive is not identified as the issuer of those documents.",
        "external_agency_assessment_or_service",
        "The proposition establishes a government authentication service but does not establish an issuing relationship for the documents.",
        contrast_group="issuer_verified_record_vs_independent_verification_service",
    ),
    case(
        "v6_032",
        "Which government transport-agency service checks the status of an overseas driver licence when a person applies for local licence conversion.",
        "external_agency_assessment_or_service",
        "This is an external government verification or administrative service, not an issuing procedure for the overseas licence.",
    ),

    # external_entitlement_or_service_regime: 4
    case(
        "v6_033",
        "Whether a person's immigration status makes them eligible for publicly funded tertiary-study fees under a separately administered education regime.",
        "external_entitlement_or_service_regime",
        "The proposition concerns eligibility for an external public education entitlement, with immigration status as an input.",
        contrast_group="instruction_rule_vs_external_entitlement",
    ),
    case(
        "v6_034",
        "Whether a temporary visa holder qualifies for subsidised primary health services under the public health eligibility rules.",
        "external_entitlement_or_service_regime",
        "This is eligibility for a separately administered public health service regime.",
    ),
    case(
        "v6_035",
        "Whether a household with a specified visa status can receive a government-administered accommodation subsidy.",
        "external_entitlement_or_service_regime",
        "This asks about access to a public benefit regime outside immigration instructions.",
    ),
    case(
        "v6_036",
        "Whether immigration status affects eligibility for a publicly funded early-childhood assistance scheme administered by an education authority.",
        "external_entitlement_or_service_regime",
        "The authoritative owner is the separately administered public-service entitlement regime.",
    ),

    # professional_or_assessor_guidance: 4
    case(
        "v6_037",
        "What evidence a professional registration council requires when assessing an overseas practitioner's competence for registration.",
        "professional_or_assessor_guidance",
        "The source owner is a professional registration and assessment authority.",
        contrast_group="government_assessment_vs_professional_assessment",
    ),
    case(
        "v6_038",
        "Which clinical criteria an authorised medical examiner applies when completing a specialist fitness assessment.",
        "professional_or_assessor_guidance",
        "Clinical assessment criteria are owned by the professional or specialist-assessor role.",
        contrast_group="immigration_rule_vs_professional_standard_ambiguity",
    ),
    case(
        "v6_039",
        "What occupational standards an approved trade licensing assessor uses to decide whether overseas experience is competent for licensing purposes.",
        "professional_or_assessor_guidance",
        "The proposition concerns standards applied by a professional or specialist assessor.",
    ),
    case(
        "v6_040",
        "What supervised-practice evidence a professional accreditation body requires before recognising an overseas-trained practitioner.",
        "professional_or_assessor_guidance",
        "The authoritative owner is a professional accreditation or assessment body.",
    ),

    # other_official_external_authority: 4
    case(
        "v6_041",
        "Which electronic traveller-declaration channel a foreign border authority requires arriving passengers to use as part of its border process.",
        "other_official_external_authority",
        "Trusted context establishes a generic official external operational owner; no more specific external source class applies.",
        context={
            "publisher_family": "other_official_authority",
            "authority_role": "other_official_operational_owner",
        },
        contrast_group="foreign_issuer_replacement_vs_generic_foreign_operation",
    ),
    case(
        "v6_042",
        "What reporting procedure an overseas customs administration requires travellers to follow when declaring specified goods.",
        "other_official_external_authority",
        "Trusted context establishes the customs administration as the generic official operational owner.",
        context={
            "publisher_family": "other_official_authority",
            "authority_role": "other_official_operational_owner",
        },
        contrast_group="generic_official_with_context_vs_ambiguous_owner",
    ),
    case(
        "v6_043",
        "Which arrival-health declaration process a foreign biosecurity authority requires incoming travellers to complete.",
        "other_official_external_authority",
        "Trusted context establishes a generic external official operational owner and no more specific source class applies.",
        context={
            "publisher_family": "other_official_authority",
            "authority_role": "other_official_operational_owner",
        },
    ),
    case(
        "v6_044",
        "Which online reporting channel an overseas customs authority requires for a specified traveller declaration.",
        "other_official_external_authority",
        "The context-gated generic external official class is established by trusted publisher and authority-role metadata.",
        context={
            "publisher_family": "other_official_authority",
            "authority_role": "other_official_operational_owner",
        },
    ),

    # unresolved: 6
    case(
        "v6_045",
        "Whether a recently circulated immigration change is already a certified rule or is only non-binding staff guidance.",
        "unresolved",
        "Without trusted context, the proposition does not establish whether the change is a certified instruction or non-Manual guidance.",
        contrast_group="certified_transition_vs_uncertain_change",
    ),
    case(
        "v6_046",
        "Which authority owns an overseas document-checking process when the description does not state whether the authority issued the document or merely performs a separate verification service.",
        "unresolved",
        "The owner role is materially ambiguous between an issuing authority and an external verification service.",
        contrast_group="issuing_role_vs_ambiguous_document_check",
    ),
    case(
        "v6_047",
        "Whether a quoted immigration dollar amount is the currently payable application charge or only an historical amount stated in an older legal reference.",
        "unresolved",
        "The proposition does not resolve whether the amount is current fee information or historical legal material.",
        contrast_group="current_value_vs_ambiguous_amount",
    ),
    case(
        "v6_048",
        "Which official organisation controls an overseas clearance requirement when the description does not identify the organisation's operational role.",
        "unresolved",
        "The responsible official role remains unspecified and the context-gated generic external class cannot be established.",
        contrast_group="generic_official_with_context_vs_ambiguous_owner",
    ),
    case(
        "v6_049",
        "Which source governs a procedural instruction mentioned in an immigration message when it is unclear whether the instruction comes from certified immigration instructions or a separate INZ guide.",
        "unresolved",
        "The authoritative source home remains ambiguous between certified instructions and context-gated non-Manual guidance.",
        contrast_group="nonmanual_with_context_vs_ambiguous_guidance",
    ),
    case(
        "v6_050",
        "Which authority's standards govern a health-related assessment mentioned in an immigration requirement when the description does not establish whether the proposition is the immigration eligibility rule or the clinician's assessment standard.",
        "unresolved",
        "The proposition leaves the source owner ambiguous between certified immigration instructions and professional or assessor guidance.",
        contrast_group="immigration_rule_vs_professional_standard_ambiguity",
    ),
]


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
            "Refusing independent-pack-v6 freeze."
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
            f"Independent pack-v6 already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    for path, expected_sha, label in (
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
            DESIGN_V4_REVIEW_PATH,
            EXPECTED_DESIGN_V4_REVIEW_SHA256,
            "Approved design-v4 human review",
        ),
    ):
        require_sha(
            path,
            expected_sha,
            label,
        )

    design_v4 = load_json(
        DESIGN_V4_PATH
    )
    design_review = load_json(
        DESIGN_V4_REVIEW_PATH
    )

    if design_v4.get("schema") != (
        "waypoint-source-boundary-classifier-design-v4"
    ):
        raise RuntimeError(
            "Unexpected design-v4 schema."
        )

    if design_review.get("schema") != (
        "waypoint-source-boundary-classifier-design-v4-human-review"
    ):
        raise RuntimeError(
            "Unexpected design-v4 human-review schema."
        )

    if design_review.get("status") != (
        "APPROVED_FRESH_INDEPENDENT_PACK_CONSTRUCTION_ONLY"
    ):
        raise RuntimeError(
            "Design-v4 review does not authorise fresh pack construction."
        )

    if design_review.get(
        "authorisations",
        {},
    ).get(
        "fresh_independent_acceptance_pack_v6_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Fresh independent pack-v6 construction is not authorised."
        )

    if len(CASES) != 50:
        raise RuntimeError(
            f"Pack v6 must contain exactly 50 cases; found {len(CASES)}."
        )

    ids = [
        item["case_id"]
        for item in CASES
    ]

    if len(set(ids)) != 50:
        raise RuntimeError(
            "Pack v6 contains duplicate case IDs."
        )

    if any(
        not case_id.startswith("v6_")
        for case_id in ids
    ):
        raise RuntimeError(
            "Every pack-v6 case ID must use the v6_ namespace."
        )

    propositions = [
        item["unsupported_proposition"]
        for item in CASES
    ]

    if len(set(propositions)) != 50:
        raise RuntimeError(
            "Pack v6 contains duplicate propositions."
        )

    class_counts = Counter(
        item["expected"]["source_class"]
        for item in CASES
    )

    if dict(class_counts) != EXPECTED_CLASS_COUNTS:
        raise RuntimeError(
            "Pack-v6 source-class distribution differs from the frozen "
            "construction design.\n"
            f"Expected: {EXPECTED_CLASS_COUNTS}\n"
            f"Actual:   {dict(class_counts)}"
        )

    if set(class_counts) != set(SOURCE_CLASSES):
        raise RuntimeError(
            "Pack v6 does not cover all 12 source classes."
        )

    # Validate all expected dependent fields.
    for item in CASES:
        source_class = item["expected"]["source_class"]

        if item["expected"] != expected(source_class):
            raise RuntimeError(
                f"{item['case_id']}: expected dependent fields do not match "
                "the frozen deterministic derivation."
            )

    # Context-gated resolved classes must include required trusted context.
    for item in CASES:
        source_class = item["expected"]["source_class"]
        context = item["trusted_source_context"]

        if source_class == "manual_instruction_transition":
            required = {
                "publisher_family": "immigration_new_zealand",
                "publication_family": "certified_amendment",
                "certification_status": "certified",
            }

            if not isinstance(context, dict):
                raise RuntimeError(
                    f"{item['case_id']}: transition case lacks context."
                )

            for key, value in required.items():
                if context.get(key) != value:
                    raise RuntimeError(
                        f"{item['case_id']}: transition context mismatch."
                    )

            if context.get("incorporation_status") not in {
                "not_yet_indexed",
                "stale_local_index",
            }:
                raise RuntimeError(
                    f"{item['case_id']}: transition incorporation status invalid."
                )

        elif source_class == "inz_non_manual_procedure_or_interpretation":
            if not isinstance(context, dict):
                raise RuntimeError(
                    f"{item['case_id']}: INZ non-Manual case lacks context."
                )

            if context.get("publisher_family") != "immigration_new_zealand":
                raise RuntimeError(
                    f"{item['case_id']}: INZ publisher context mismatch."
                )

            if context.get("publication_family") not in {
                "inz_iac",
                "inz_advice_to_staff",
                "inz_form_or_guide",
            }:
                raise RuntimeError(
                    f"{item['case_id']}: INZ publication-family context invalid."
                )

        elif source_class == "other_official_external_authority":
            if not isinstance(context, dict):
                raise RuntimeError(
                    f"{item['case_id']}: generic official case lacks context."
                )

            if context.get("publisher_family") != "other_official_authority":
                raise RuntimeError(
                    f"{item['case_id']}: generic official publisher mismatch."
                )

            if context.get("authority_role") != (
                "other_official_operational_owner"
            ):
                raise RuntimeError(
                    f"{item['case_id']}: generic official authority role mismatch."
                )

    # All unresolved cases intentionally have no trusted context.
    unresolved_cases = [
        item
        for item in CASES
        if item["expected"]["source_class"] == "unresolved"
    ]

    if len(unresolved_cases) != 6:
        raise RuntimeError(
            "Pack v6 must contain exactly 6 unresolved cases."
        )

    if any(
        item["trusted_source_context"] is not None
        for item in unresolved_cases
    ):
        raise RuntimeError(
            "Fresh unresolved cases must not depend on trusted context."
        )

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for item in CASES:
        group = item.get("contrast_group")

        if group:
            groups[group].append(item)

    if len(groups) != 15:
        raise RuntimeError(
            f"Pack v6 must contain exactly 15 contrast groups; found {len(groups)}."
        )

    for group, members in groups.items():
        if len(members) < 2:
            raise RuntimeError(
                f"Contrast group {group!r} must contain at least two members."
            )

        classes = {
            item["expected"]["source_class"]
            for item in members
        }

        if len(classes) < 2:
            raise RuntimeError(
                f"Contrast group {group!r} must span at least two source classes."
            )

    required_group_names = {
        "instruction_condition_vs_live_service",
        "instruction_requirement_vs_statutory_power",
        "instruction_exception_vs_nonmanual_process",
        "instruction_rule_vs_external_entitlement",
        "certified_transition_vs_uncertain_change",
        "current_value_vs_ambiguous_amount",
        "legal_levy_basis_vs_current_levy_amount",
        "live_service_vs_current_fee",
        "nonmanual_with_context_vs_ambiguous_guidance",
        "foreign_issuer_replacement_vs_generic_foreign_operation",
        "issuer_verified_record_vs_independent_verification_service",
        "government_assessment_vs_professional_assessment",
        "generic_official_with_context_vs_ambiguous_owner",
        "issuing_role_vs_ambiguous_document_check",
        "immigration_rule_vs_professional_standard_ambiguity",
    }

    if set(groups) != required_group_names:
        raise RuntimeError(
            "Pack-v6 contrast-group set differs from the frozen construction."
        )

    artifact = {
        "schema": (
            "waypoint-source-boundary-classifier-independent-contract-test-pack-v6"
        ),
        "status": (
            "FROZEN_FRESH_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW"
        ),
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": (
                EXPECTED_RUNTIME_SHA256
            ),
            "classifier_design_v4_sha256": (
                EXPECTED_DESIGN_V4_SHA256
            ),
            "classifier_design_v4_human_review_sha256": (
                EXPECTED_DESIGN_V4_REVIEW_SHA256
            ),
        },
        "construction_provenance": {
            "design_source": "classifier_design_v4",
            "design_review_source": (
                "classifier_design_v4_human_review"
            ),
            "previous_acceptance_pack_read": False,
            "previous_predictions_read": False,
            "previous_scores_read": False,
            "previous_failure_analysis_read": False,
            "model_calls": 0,
            "prior_case_ids_used": False,
            "prior_case_literals_intentionally_copied": False,
        },
        "pack_contract": {
            "case_count": 50,
            "resolved_case_count": 44,
            "unresolved_case_count": 6,
            "source_class_count": 12,
            "resolved_cases_per_source_class": 4,
            "contrast_group_count": 15,
            "all_contrast_groups_span_multiple_classes": True,
            "all_three_context_gates_covered": True,
            "foreign_issuing_external_agency_boundary_covered": True,
            "semantic_non_gated_resolution_without_context_covered": True,
            "unresolved_ambiguity_covered": True,
        },
        "source_class_distribution": (
            EXPECTED_CLASS_COUNTS
        ),
        "contrast_groups": {
            group: {
                "members": [
                    item["case_id"]
                    for item in members
                ],
                "source_classes": sorted(
                    {
                        item["expected"]["source_class"]
                        for item in members
                    }
                ),
            }
            for group, members in sorted(groups.items())
        },
        "tests": CASES,
        "methodology": {
            "fresh_independent_acceptance_candidate": True,
            "human_review_required_before_threshold_freeze": True,
            "human_review_required_before_implementation": True,
            "thresholds_must_be_frozen_before_predictions": True,
            "pack_must_not_be_modified_after_human_review": True,
            "model_must_not_see_expected_outputs": True,
            "model_must_not_see_basis": True,
            "model_must_not_see_contrast_group": True,
            "case_id_must_not_be_passed_to_model": True,
            "all_acceptance_gates_required": True,
            "manual_override": False,
            "automatic_retry": False,
        },
        "authorisations": {
            "fresh_pack_v6_human_review_authorised": True,
            "acceptance_thresholds_v3_construction_authorised": False,
            "classifier_prompt_v3_construction_authorised": False,
            "classifier_implementation_v3_construction_authorised": False,
            "blind_input_v3_construction_authorised": False,
            "classifier_model_run_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "source_boundary_classifier_independent_pack_v6_human_review"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Human-review the fresh 50-case pack for gold validity, "
                "contrast semantics, design-v4 alignment, context-gate "
                "coverage, independence, and absence of benchmark-specific "
                "construction defects before thresholds or implementation."
            ),
        },
    }

    artifact_text = json.dumps(
        artifact,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    # Independence guard: no old case-ID namespaces.
    for forbidden_literal in (
        "iv4_",
        "sbv2_",
    ):
        if forbidden_literal in artifact_text:
            raise RuntimeError(
                "Fresh pack contains a prior case-ID namespace: "
                + forbidden_literal
            )

    OUTPUT_PATH.write_text(
        artifact_text,
        encoding="utf-8",
    )

    saved = load_json(
        OUTPUT_PATH
    )

    if saved.get("status") != (
        "FROZEN_FRESH_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Saved pack-v6 status changed."
        )

    if len(saved.get("tests", [])) != 50:
        raise RuntimeError(
            "Saved pack-v6 case count changed."
        )

    saved_auth = saved.get(
        "authorisations",
        {},
    )

    if saved_auth.get(
        "fresh_pack_v6_human_review_authorised"
    ) is not True:
        raise RuntimeError(
            "Pack-v6 human review was not authorised."
        )

    for forbidden in (
        "acceptance_thresholds_v3_construction_authorised",
        "classifier_prompt_v3_construction_authorised",
        "classifier_implementation_v3_construction_authorised",
        "blind_input_v3_construction_authorised",
        "classifier_model_run_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(forbidden) is not False:
            raise RuntimeError(
                f"Pack v6 unexpectedly authorises {forbidden}."
            )

    print("Waypoint source-boundary classifier independent contract pack v6")
    print("=" * 76)
    print(
        f"Design-v4 SHA256:           "
        f"{sha256(DESIGN_V4_PATH)}"
    )
    print(
        f"Design-v4 review SHA256:    "
        f"{sha256(DESIGN_V4_REVIEW_PATH)}"
    )
    print()
    print("Construction isolation")
    print("-" * 76)
    print("Previous pack read:         NO")
    print("Previous predictions read:  NO")
    print("Previous scores read:       NO")
    print("Failure analysis read:      NO")
    print("Prior case-ID namespaces:   NONE")
    print("Model calls:                NONE")
    print()
    print("Pack structure")
    print("-" * 76)
    print("Cases:                      50")
    print("Resolved cases:             44")
    print("Unresolved cases:           6")
    print("Source classes:             12/12")
    print("Resolved cases/class:       4 each")
    print("Contrast groups:            15")
    print("Contrast groups multi-class:15/15")
    print()
    print("Design-v4 coverage")
    print("-" * 76)
    print("All 3 context gates:        YES")
    print("Foreign issuer boundary:    YES")
    print("External agency boundary:   YES")
    print("Non-gated semantic cases:   YES")
    print("Unresolved ambiguity:       YES")
    print()
    print("Pack-v6 human review:       AUTHORISED")
    print("Threshold-v3 construction:  NOT AUTHORISED")
    print("Prompt-v3 construction:     NOT AUTHORISED")
    print("Implementation-v3:          NOT AUTHORISED")
    print("Blind-input-v3:             NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  PACK-V6 HUMAN REVIEW")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(
        f"Pack-v6 SHA256:             "
        f"{sha256(OUTPUT_PATH)}"
    )
    print()
    print("Runtime files modified:     NONE")
    print()
    print("Independent contract pack v6 freeze: PASS")


if __name__ == "__main__":
    main()
