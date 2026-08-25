"""Freeze replacement independent contract test pack v7 for Waypoint.

CONSTRUCTION ONLY.
- No model calls.
- Built from frozen classifier design v4, its approved human review, and the
  pack-v6 rejection authorisation.
- Does NOT read pack v5.
- Does NOT read pack v6.
- Does NOT read prior predictions, scores, or failure-analysis artifacts.
- Uses materially different concrete scenario families from the rejected pack.
- Must be human-reviewed against prior packs after freezing.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_independent_pack_v7.py
    uv run python -m scripts.freeze_source_boundary_classifier_independent_pack_v7

Output:
    tests/source_boundary_classifier_independent_contract_test_pack_v7.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent.parent
RUNTIME_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
DESIGN_V4_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_design_v4.json"
DESIGN_V4_REVIEW_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_design_v4_human_review.json"
PACK_V6_REVIEW_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_independent_pack_human_review_v6.json"
OUTPUT_PATH = BACKEND_DIR / "tests" / "source_boundary_classifier_independent_contract_test_pack_v7.json"

EXPECTED_RUNTIME_SHA256 = "FF879300C09B195681E109E5B4F5D807C89216E986AE4AA9338B104FA99AAD0E"
EXPECTED_DESIGN_V4_SHA256 = "9563158E74CFBC0C7D25D2DC2BA8FC2036E0B32193BADDFBE464ECCB99329948"
EXPECTED_DESIGN_V4_REVIEW_SHA256 = "4456BEE89A249043510730BF5A01FCE05EF0A6C49EDF39FAD2EBBB55E17D9AD5"
EXPECTED_PACK_V6_REVIEW_SHA256 = "5A0B8C5E6C6C231710B50CE5A2D6A9648CECB18F2E8F07AACDF028BF0B4670C4"

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

EXPECTED_GROUP_NAMES = {
    "visa_condition_vs_live_office_state",
    "visa_rule_vs_statutory_detention_power",
    "partnership_rule_vs_public_legal_aid",
    "certified_transition_vs_uncertified_future_notice",
    "live_callback_vs_current_document_return_charge",
    "inz_guide_vs_unverified_staff_checklist",
    "issuer_verified_identity_card_vs_independent_identity_match",
    "foreign_issuer_vs_external_revenue_operation",
    "government_recognition_service_vs_professional_registration",
    "generic_official_context_vs_unverified_municipal_process",
    "external_agency_service_vs_ambiguous_assessor_owner",
    "live_payment_state_vs_rule_or_outage_ambiguity",
    "current_transaction_charge_vs_payment_or_funds_ambiguity",
    "statutory_search_power_vs_operational_secondary_applicant_rule",
}

DERIVATION = {
    "operational_manual_instruction": {"resolution_status": "resolved", "source_domain": "certified_immigration_instructions", "responsible_authority_type": "immigration_new_zealand"},
    "manual_instruction_transition": {"resolution_status": "resolved", "source_domain": "certified_immigration_instructions", "responsible_authority_type": "immigration_new_zealand"},
    "legislation_or_regulation": {"resolution_status": "resolved", "source_domain": "legislation_or_regulation", "responsible_authority_type": "new_zealand_legislature_or_regulator"},
    "inz_live_service_information": {"resolution_status": "resolved", "source_domain": "official_inz_non_manual", "responsible_authority_type": "immigration_new_zealand"},
    "current_fee_or_charge_information": {"resolution_status": "resolved", "source_domain": "official_inz_non_manual", "responsible_authority_type": "immigration_new_zealand"},
    "inz_non_manual_procedure_or_interpretation": {"resolution_status": "resolved", "source_domain": "official_inz_non_manual", "responsible_authority_type": "immigration_new_zealand"},
    "foreign_issuing_authority_procedure": {"resolution_status": "resolved", "source_domain": "responsible_external_official_authority", "responsible_authority_type": "foreign_issuing_authority"},
    "external_agency_assessment_or_service": {"resolution_status": "resolved", "source_domain": "responsible_external_official_authority", "responsible_authority_type": "external_government_agency"},
    "external_entitlement_or_service_regime": {"resolution_status": "resolved", "source_domain": "responsible_external_official_authority", "responsible_authority_type": "public_service_authority"},
    "professional_or_assessor_guidance": {"resolution_status": "resolved", "source_domain": "responsible_external_official_authority", "responsible_authority_type": "professional_or_assessment_authority"},
    "other_official_external_authority": {"resolution_status": "resolved", "source_domain": "responsible_external_official_authority", "responsible_authority_type": "other_official_authority"},
    "unresolved": {"resolution_status": "unresolved", "source_domain": "unresolved", "responsible_authority_type": "unresolved"},
}


def expected_fields(source_class: str) -> dict[str, str]:
    derived = DERIVATION[source_class]
    return {
        "resolution_status": derived["resolution_status"],
        "source_domain": derived["source_domain"],
        "source_class": source_class,
        "responsible_authority_type": derived["responsible_authority_type"],
    }


def make_case(case_id: str, proposition: str, source_class: str, basis: str, *, context: dict[str, str] | None = None, contrast_group: str | None = None) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "unsupported_proposition": proposition,
        "trusted_source_context": context,
        "expected": expected_fields(source_class),
        "basis": basis,
        "contrast_group": contrast_group,
    }


CASES = [
    make_case("v7_001", "Whether a student visa holder must remain enrolled in a full-time programme to continue meeting the conditions of that visa.", "operational_manual_instruction", "This is a substantive immigration condition attached to continued visa compliance.", contrast_group="visa_condition_vs_live_office_state"),
    make_case("v7_002", "Whether a partnership-based applicant must be living together with the supporting partner when the application is assessed.", "operational_manual_instruction", "This is an instruction-defined partnership eligibility requirement.", contrast_group="partnership_rule_vs_public_legal_aid"),
    make_case("v7_003", "Whether the conditions of a specified work visa permit the holder to undertake self-employment.", "operational_manual_instruction", "This is a substantive permission or restriction defined by certified immigration instructions.", contrast_group="visa_rule_vs_statutory_detention_power"),
    make_case("v7_004", "Whether certified immigration instructions allow a secondary applicant to be added after the principal applicant has already been granted the relevant visa.", "operational_manual_instruction", "This is an instruction-defined rule about secondary-applicant inclusion.", contrast_group="statutory_search_power_vs_operational_secondary_applicant_rule"),

    make_case("v7_005", "Whether a certified amendment changing the validity period accepted for an English-language test applies even though the local instruction index still shows the former period.", "manual_instruction_transition", "Trusted context establishes an authoritative certified amendment with a stale local index.", context={"publisher_family": "immigration_new_zealand", "publication_family": "certified_amendment", "certification_status": "certified", "incorporation_status": "stale_local_index"}, contrast_group="certified_transition_vs_uncertified_future_notice"),
    make_case("v7_006", "Which relationship-evidence requirement governs after a certified immigration amendment has taken effect but has not yet appeared in the local instruction index.", "manual_instruction_transition", "The trusted metadata establishes a certified amendment that is not yet indexed locally.", context={"publisher_family": "immigration_new_zealand", "publication_family": "certified_amendment", "certification_status": "certified", "incorporation_status": "not_yet_indexed"}),
    make_case("v7_007", "Whether newly certified instructions changing the number of hours a visa holder may study apply before the locally indexed text is refreshed.", "manual_instruction_transition", "This is a certified INZ amendment in force while the local index remains stale.", context={"publisher_family": "immigration_new_zealand", "publication_family": "certified_amendment", "certification_status": "certified", "incorporation_status": "stale_local_index"}),
    make_case("v7_008", "Which health-insurance evidence rule applies when a certified amendment is effective but the local instruction collection has not yet incorporated it.", "manual_instruction_transition", "Trusted context establishes a certified amendment not yet indexed locally.", context={"publisher_family": "immigration_new_zealand", "publication_family": "certified_amendment", "certification_status": "certified", "incorporation_status": "not_yet_indexed"}),

    make_case("v7_009", "Which statutory provision gives immigration authorities legal power to detain a person for a prescribed deportation-related purpose.", "legislation_or_regulation", "This asks for the statutory source of a coercive legal power.", contrast_group="visa_rule_vs_statutory_detention_power"),
    make_case("v7_010", "What enactment authorises an immigration officer to search a vehicle or craft in circumstances specified by law.", "legislation_or_regulation", "The proposition concerns legal authority for a statutory search power.", contrast_group="statutory_search_power_vs_operational_secondary_applicant_rule"),
    make_case("v7_011", "Which legal provision permits specified immigration powers to be delegated to another authorised decision-maker.", "legislation_or_regulation", "The authoritative home is legislation because the proposition concerns legal delegation of statutory power."),
    make_case("v7_012", "Which regulation or enactment creates a legal offence for knowingly presenting a fraudulent document in an immigration process.", "legislation_or_regulation", "This is a legal offence proposition rather than an operational eligibility or processing rule."),

    make_case("v7_013", "Whether an Immigration New Zealand service office is open to customers today after an unexpected local closure notice.", "inz_live_service_information", "Current office availability is a time-varying INZ service state.", contrast_group="visa_condition_vs_live_office_state"),
    make_case("v7_014", "Whether telephone callback appointments are currently available through an Immigration New Zealand contact service.", "inz_live_service_information", "Current callback availability is live operational service information.", contrast_group="live_callback_vs_current_document_return_charge"),
    make_case("v7_015", "What waiting time Immigration New Zealand currently displays for customers using a specified identity-verification service.", "inz_live_service_information", "A currently displayed service wait is a time-varying operational value."),
    make_case("v7_016", "Whether Immigration New Zealand's online payment service is currently functioning for new application payments.", "inz_live_service_information", "Current availability of a payment service is a live service state, not the amount of a fee.", contrast_group="live_payment_state_vs_rule_or_outage_ambiguity"),

    make_case("v7_017", "What Immigration New Zealand currently charges for a specified document-return or courier service connected with an application.", "current_fee_or_charge_information", "The proposition asks for a currently payable service charge.", contrast_group="live_callback_vs_current_document_return_charge"),
    make_case("v7_018", "What application fee is currently payable when a specified immigration application is lodged using the paper channel rather than online.", "current_fee_or_charge_information", "This asks for a current channel-specific application charge."),
    make_case("v7_019", "What fee Immigration New Zealand currently charges for transferring an existing visa record to a replacement travel document.", "current_fee_or_charge_information", "The proposition asks for a current payable immigration service amount."),
    make_case("v7_020", "What transaction surcharge is currently added when a specified Immigration New Zealand payment method is used.", "current_fee_or_charge_information", "This is a current payable transaction-related charge.", contrast_group="current_transaction_charge_vs_payment_or_funds_ambiguity"),

    make_case("v7_021", "What an Immigration New Zealand internal administration circular tells staff to do when supporting scans are unreadable but the application can still be identified.", "inz_non_manual_procedure_or_interpretation", "Trusted context identifies an INZ internal administration circular.", context={"publisher_family": "immigration_new_zealand", "publication_family": "inz_iac"}),
    make_case("v7_022", "How an Immigration New Zealand Advice to Staff publication directs officers to record the use of an interpreter during processing.", "inz_non_manual_procedure_or_interpretation", "Trusted context identifies an INZ Advice to Staff publication.", context={"publisher_family": "immigration_new_zealand", "publication_family": "inz_advice_to_staff"}),
    make_case("v7_023", "What an Immigration New Zealand application guide says applicants must provide when a supporting document is translated into English.", "inz_non_manual_procedure_or_interpretation", "Trusted context identifies an INZ form or guide containing procedural instructions.", context={"publisher_family": "immigration_new_zealand", "publication_family": "inz_form_or_guide"}, contrast_group="inz_guide_vs_unverified_staff_checklist"),
    make_case("v7_024", "Where an Immigration New Zealand form guide tells a parent to attach consent evidence for a minor applicant.", "inz_non_manual_procedure_or_interpretation", "Trusted context identifies a non-Manual INZ form or guide.", context={"publisher_family": "immigration_new_zealand", "publication_family": "inz_form_or_guide"}),

    make_case("v7_025", "How the foreign revenue authority that issued a person's tax-residency certificate allows the person to request a replacement certificate.", "foreign_issuing_authority_procedure", "The authority is explicitly identified as issuer of the relevant official record.", contrast_group="foreign_issuer_vs_external_revenue_operation"),
    make_case("v7_026", "What process the national identity authority that issued a person's identity card requires to replace the card after loss.", "foreign_issuing_authority_procedure", "The proposition clearly establishes the authority's issuing role for the identity document."),
    make_case("v7_027", "How the overseas vehicle-licensing authority that issued a person's driving licence provides an official certified duplicate of that licence.", "foreign_issuing_authority_procedure", "The relevant foreign authority is explicitly acting as issuer of the licence record."),
    make_case("v7_028", "How a national identity authority confirms the authenticity of an identity card that the same authority issued.", "foreign_issuing_authority_procedure", "Verification falls within the issuing class because issuer identity for the same document is explicitly established.", contrast_group="issuer_verified_identity_card_vs_independent_identity_match"),

    make_case("v7_029", "Which recognition service a government education ministry provides to determine whether an overseas school is officially recognised in its home system.", "external_agency_assessment_or_service", "This is a government-agency recognition service rather than a professional registration assessment.", contrast_group="government_recognition_service_vs_professional_registration"),
    make_case("v7_030", "Which identity-matching service a government digital-services agency provides to compare submitted personal details with official databases, without issuing the identity document being checked.", "external_agency_assessment_or_service", "The proposition establishes an independent government verification service and explicitly excludes an issuing role.", contrast_group="issuer_verified_identity_card_vs_independent_identity_match"),
    make_case("v7_031", "Which government transport-safety service assesses whether an overseas vehicle registration is acceptable for a local import process.", "external_agency_assessment_or_service", "This is an external government administrative assessment service.", contrast_group="external_agency_service_vs_ambiguous_assessor_owner"),
    make_case("v7_032", "Which government records-search service provides a person's recorded international travel movements from an official database.", "external_agency_assessment_or_service", "This is an external government administrative information service, not a document-issuing procedure for a pre-existing foreign record."),

    make_case("v7_033", "Whether a person's immigration status affects eligibility for publicly funded legal aid under a separately administered justice-service regime.", "external_entitlement_or_service_regime", "The proposition concerns eligibility for an external public entitlement, with immigration status as an input.", contrast_group="partnership_rule_vs_public_legal_aid"),
    make_case("v7_034", "Whether a temporary visa holder can receive a government public-transport concession administered outside the immigration system.", "external_entitlement_or_service_regime", "This is eligibility for a separately administered public-service concession."),
    make_case("v7_035", "Whether immigration status is one of the eligibility inputs for a government emergency-income-support payment.", "external_entitlement_or_service_regime", "The authoritative owner is a public benefit regime outside immigration instructions."),
    make_case("v7_036", "Whether a visa holder qualifies for a publicly funded adult vocational-training subsidy administered by another government authority.", "external_entitlement_or_service_regime", "This asks about access to a separately administered public-service subsidy."),

    make_case("v7_037", "What supervised-teaching evidence a teacher registration body requires when assessing an overseas-trained teacher for professional registration.", "professional_or_assessor_guidance", "The authoritative owner is a professional registration and assessment body.", contrast_group="government_recognition_service_vs_professional_registration"),
    make_case("v7_038", "Which medical fitness criteria an authorised aviation medical examiner applies when certifying a pilot.", "professional_or_assessor_guidance", "Clinical fitness criteria are owned by a specialist professional assessor."),
    make_case("v7_039", "What competency evidence an engineering registration authority requires when assessing an overseas-trained engineer.", "professional_or_assessor_guidance", "The proposition concerns competence standards owned by a professional registration authority."),
    make_case("v7_040", "Which practical assessment standards an electrical licensing body applies before recognising an overseas-trained electrician.", "professional_or_assessor_guidance", "The source owner is a professional or specialist licensing assessor."),

    make_case("v7_041", "Which departure-tax declaration process a foreign revenue administration requires travellers to complete before leaving the country.", "other_official_external_authority", "Trusted context establishes a generic official operational owner, and no more specific source class applies.", context={"publisher_family": "other_official_authority", "authority_role": "other_official_operational_owner"}, contrast_group="foreign_issuer_vs_external_revenue_operation"),
    make_case("v7_042", "Which online registration channel a foreign municipal authority requires accommodation providers to use when registering short-term guests.", "other_official_external_authority", "Trusted context establishes the municipal authority as the generic official operational owner.", context={"publisher_family": "other_official_authority", "authority_role": "other_official_operational_owner"}, contrast_group="generic_official_context_vs_unverified_municipal_process"),
    make_case("v7_043", "What workplace-incident notification procedure a foreign labour inspectorate requires employers to follow.", "other_official_external_authority", "Trusted context establishes a generic external official operational owner.", context={"publisher_family": "other_official_authority", "authority_role": "other_official_operational_owner"}),
    make_case("v7_044", "Which overseas-voter registration process a foreign electoral commission requires citizens abroad to use for a specified election.", "other_official_external_authority", "Trusted context establishes the electoral commission as a generic official operational owner.", context={"publisher_family": "other_official_authority", "authority_role": "other_official_operational_owner"}),

    make_case("v7_045", "Whether an immigration application route shown as unavailable is blocked by a substantive filing rule or is only temporarily unavailable because the online payment service is down.", "unresolved", "The proposition does not resolve whether the authoritative home is a certified immigration rule or a live service state.", contrast_group="live_payment_state_vs_rule_or_outage_ambiguity"),
    make_case("v7_046", "Which authority owns an overseas teaching-credential assessment when the description does not establish whether a government education agency or a professional teacher-registration body performs the assessment.", "unresolved", "The source owner is materially ambiguous between an external government agency and a professional registration authority.", contrast_group="external_agency_service_vs_ambiguous_assessor_owner"),
    make_case("v7_047", "Whether a stated immigration-related amount is a fee that must be paid now or an instruction-defined amount of funds that the applicant only needs to hold as evidence.", "unresolved", "The proposition does not establish whether the amount is a current payable charge or a substantive financial-evidence requirement.", contrast_group="current_transaction_charge_vs_payment_or_funds_ambiguity"),
    make_case("v7_048", "Which rule governs a foreign municipal guest-registration process when the description mentions a local authority but provides no trusted source metadata establishing the authority's operational-owner role.", "unresolved", "The generic external-official class is context-gated, and the required trusted authority-role context is absent.", contrast_group="generic_official_context_vs_unverified_municipal_process"),
    make_case("v7_049", "Which source owns a staff checklist about translated documents when the description does not establish that the checklist is an official Immigration New Zealand guide, circular, or Advice to Staff publication.", "unresolved", "The context-gated INZ non-Manual publication class cannot be established from the proposition alone.", contrast_group="inz_guide_vs_unverified_staff_checklist"),
    make_case("v7_050", "Whether an announced future change to accepted English-test validity is already an authoritative certified immigration amendment when no trusted certification or incorporation metadata is available.", "unresolved", "The context-gated transition class cannot be established without trusted certified-amendment metadata.", contrast_group="certified_transition_vs_uncertified_future_notice"),
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(path: Path, expected_sha: str, label: str) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")
    actual = sha256(path)
    if actual != expected_sha:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Expected: {expected_sha}\n"
            f"Actual:   {actual}\n"
            "Refusing independent-pack-v7 freeze."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")
    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(f"Independent pack-v7 already exists: {OUTPUT_PATH}\nRefusing to overwrite it.")

    for path, expected_sha, label in (
        (RUNTIME_PATH, EXPECTED_RUNTIME_SHA256, "Frozen production candidate-v2 runtime"),
        (DESIGN_V4_PATH, EXPECTED_DESIGN_V4_SHA256, "Frozen classifier design v4"),
        (DESIGN_V4_REVIEW_PATH, EXPECTED_DESIGN_V4_REVIEW_SHA256, "Approved design-v4 human review"),
        (PACK_V6_REVIEW_PATH, EXPECTED_PACK_V6_REVIEW_SHA256, "Frozen pack-v6 human rejection review"),
    ):
        require_sha(path, expected_sha, label)

    design_v4 = load_json(DESIGN_V4_PATH)
    design_review = load_json(DESIGN_V4_REVIEW_PATH)
    pack_v6_review = load_json(PACK_V6_REVIEW_PATH)

    if design_v4.get("schema") != "waypoint-source-boundary-classifier-design-v4":
        raise RuntimeError("Unexpected design-v4 schema.")
    if design_review.get("status") != "APPROVED_FRESH_INDEPENDENT_PACK_CONSTRUCTION_ONLY":
        raise RuntimeError("Design-v4 human review status changed.")
    if pack_v6_review.get("status") != "REJECTED_FRESHNESS_INDEPENDENCE_REBUILD_REQUIRED":
        raise RuntimeError("Pack-v6 human review does not require replacement.")
    if pack_v6_review.get("authorisations", {}).get("independent_pack_v7_construction_authorised") is not True:
        raise RuntimeError("Independent pack-v7 construction is not authorised.")

    if len(CASES) != 50:
        raise RuntimeError(f"Pack v7 must contain exactly 50 cases; found {len(CASES)}.")

    ids = [item["case_id"] for item in CASES]
    propositions = [item["unsupported_proposition"] for item in CASES]
    if len(set(ids)) != 50:
        raise RuntimeError("Pack v7 contains duplicate case IDs.")
    if any(not case_id.startswith("v7_") for case_id in ids):
        raise RuntimeError("Every pack-v7 case ID must use the v7_ namespace.")
    if len(set(propositions)) != 50:
        raise RuntimeError("Pack v7 contains duplicate propositions.")

    class_counts = Counter(item["expected"]["source_class"] for item in CASES)
    if dict(class_counts) != EXPECTED_CLASS_COUNTS:
        raise RuntimeError(f"Pack-v7 source-class distribution differs from design.\nExpected: {EXPECTED_CLASS_COUNTS}\nActual:   {dict(class_counts)}")
    if set(class_counts) != set(SOURCE_CLASSES):
        raise RuntimeError("Pack v7 does not cover all 12 source classes.")

    for item in CASES:
        source_class = item["expected"]["source_class"]
        if item["expected"] != expected_fields(source_class):
            raise RuntimeError(f"{item['case_id']}: expected dependent fields do not match the frozen deterministic derivation.")

    for item in CASES:
        source_class = item["expected"]["source_class"]
        context = item["trusted_source_context"]
        if source_class == "manual_instruction_transition":
            if not isinstance(context, dict):
                raise RuntimeError(f"{item['case_id']}: transition case lacks context.")
            for key, value in {"publisher_family": "immigration_new_zealand", "publication_family": "certified_amendment", "certification_status": "certified"}.items():
                if context.get(key) != value:
                    raise RuntimeError(f"{item['case_id']}: transition context mismatch.")
            if context.get("incorporation_status") not in {"not_yet_indexed", "stale_local_index"}:
                raise RuntimeError(f"{item['case_id']}: invalid incorporation status.")
        elif source_class == "inz_non_manual_procedure_or_interpretation":
            if not isinstance(context, dict):
                raise RuntimeError(f"{item['case_id']}: INZ non-Manual case lacks context.")
            if context.get("publisher_family") != "immigration_new_zealand":
                raise RuntimeError(f"{item['case_id']}: INZ publisher context mismatch.")
            if context.get("publication_family") not in {"inz_iac", "inz_advice_to_staff", "inz_form_or_guide"}:
                raise RuntimeError(f"{item['case_id']}: invalid INZ publication family.")
        elif source_class == "other_official_external_authority":
            if not isinstance(context, dict):
                raise RuntimeError(f"{item['case_id']}: generic external class lacks context.")
            if context.get("publisher_family") != "other_official_authority":
                raise RuntimeError(f"{item['case_id']}: external publisher mismatch.")
            if context.get("authority_role") != "other_official_operational_owner":
                raise RuntimeError(f"{item['case_id']}: external authority-role mismatch.")

    unresolved_cases = [item for item in CASES if item["expected"]["source_class"] == "unresolved"]
    if len(unresolved_cases) != 6:
        raise RuntimeError("Pack v7 must contain exactly 6 unresolved cases.")
    if any(item["trusted_source_context"] is not None for item in unresolved_cases):
        raise RuntimeError("Pack-v7 unresolved cases must not contain trusted context.")

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in CASES:
        group = item.get("contrast_group")
        if isinstance(group, str) and group:
            groups[group].append(item)

    if set(groups) != EXPECTED_GROUP_NAMES:
        raise RuntimeError(f"Pack-v7 contrast-group set differs from the frozen construction.\nExpected: {sorted(EXPECTED_GROUP_NAMES)}\nActual:   {sorted(groups)}")
    if len(groups) != 14:
        raise RuntimeError(f"Pack v7 must contain 14 contrast groups; found {len(groups)}.")
    for group, members in groups.items():
        if len(members) < 2:
            raise RuntimeError(f"Contrast group {group!r} has fewer than 2 members.")
        classes = {item["expected"]["source_class"] for item in members}
        if len(classes) < 2:
            raise RuntimeError(f"Contrast group {group!r} does not span multiple classes.")

    artifact = {
        "schema": "waypoint-source-boundary-classifier-independent-contract-test-pack-v7",
        "status": "FROZEN_REPLACEMENT_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW",
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "classifier_design_v4_sha256": EXPECTED_DESIGN_V4_SHA256,
            "classifier_design_v4_human_review_sha256": EXPECTED_DESIGN_V4_REVIEW_SHA256,
            "pack_v6_human_rejection_review_sha256": EXPECTED_PACK_V6_REVIEW_SHA256,
        },
        "construction_provenance": {
            "design_v4_read": True,
            "design_v4_human_review_read": True,
            "pack_v6_rejection_authorisation_read": True,
            "pack_v5_read": False,
            "pack_v6_read": False,
            "prior_predictions_read": False,
            "prior_scores_read": False,
            "prior_failure_analysis_read": False,
            "model_calls": 0,
            "prior_case_id_namespaces_used": False,
            "materially_different_scenario_families_intended": True,
        },
        "pack_contract": {
            "case_count": 50,
            "resolved_case_count": 44,
            "unresolved_case_count": 6,
            "source_class_count": 12,
            "resolved_cases_per_source_class": 4,
            "contrast_group_count": 14,
            "all_contrast_groups_span_multiple_classes": True,
            "all_three_context_gates_covered": True,
            "foreign_issuing_external_agency_boundary_covered": True,
            "semantic_non_gated_resolution_without_context_covered": True,
            "unresolved_ambiguity_covered": True,
        },
        "source_class_distribution": EXPECTED_CLASS_COUNTS,
        "contrast_groups": {
            group: {
                "members": [item["case_id"] for item in members],
                "source_classes": sorted({item["expected"]["source_class"] for item in members}),
            }
            for group, members in sorted(groups.items())
        },
        "tests": CASES,
        "methodology": {
            "replacement_fresh_acceptance_candidate": True,
            "human_review_required_against_prior_packs": True,
            "human_review_required_before_threshold_freeze": True,
            "human_review_required_before_implementation": True,
            "thresholds_must_be_frozen_before_predictions": True,
            "pack_must_not_be_modified_after_human_approval": True,
            "model_must_not_see_expected_outputs": True,
            "model_must_not_see_basis": True,
            "model_must_not_see_contrast_group": True,
            "case_id_must_not_be_passed_to_model": True,
            "all_acceptance_gates_required": True,
            "manual_override": False,
            "automatic_retry": False,
        },
        "authorisations": {
            "independent_pack_v7_human_review_authorised": True,
            "acceptance_thresholds_v3_construction_authorised": False,
            "classifier_prompt_v3_construction_authorised": False,
            "classifier_implementation_v3_construction_authorised": False,
            "blind_input_v3_construction_authorised": False,
            "classifier_model_run_authorised": False,
            "classifier_rerun_on_pack_v5_authorised": False,
            "classifier_run_on_pack_v6_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_independent_pack_v7_human_review",
            "authorised": True,
            "model_calls": 0,
            "purpose": "Human-review replacement pack v7 for gold validity, design-v4 coverage, contrast semantics, and content-level independence from previously observed packs before thresholds or implementation v3 are authorised.",
        },
    }

    artifact_text = json.dumps(artifact, indent=2, ensure_ascii=False) + "\n"

    # Check prior namespaces only in actual case_id values. Provenance and
    # authorisation metadata may legitimately refer to pack-v6 artifacts.
    forbidden_case_id_prefixes = ("iv4_", "v6_", "sbv2_")
    leaked_case_ids = [
        item["case_id"]
        for item in CASES
        if item["case_id"].startswith(forbidden_case_id_prefixes)
    ]

    if leaked_case_ids:
        raise RuntimeError(
            "Pack-v7 contains prior case-ID namespaces in case_id values: "
            + ", ".join(leaked_case_ids)
        )

    OUTPUT_PATH.write_text(artifact_text, encoding="utf-8")
    saved = load_json(OUTPUT_PATH)
    if saved.get("status") != "FROZEN_REPLACEMENT_INDEPENDENT_PACK_READY_FOR_HUMAN_REVIEW":
        raise RuntimeError("Saved pack-v7 status changed.")
    if len(saved.get("tests", [])) != 50:
        raise RuntimeError("Saved pack-v7 case count changed.")

    saved_auth = saved.get("authorisations", {})
    if saved_auth.get("independent_pack_v7_human_review_authorised") is not True:
        raise RuntimeError("Pack-v7 human review was not authorised.")
    for forbidden in (
        "acceptance_thresholds_v3_construction_authorised",
        "classifier_prompt_v3_construction_authorised",
        "classifier_implementation_v3_construction_authorised",
        "blind_input_v3_construction_authorised",
        "classifier_model_run_authorised",
        "classifier_rerun_on_pack_v5_authorised",
        "classifier_run_on_pack_v6_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(forbidden) is not False:
            raise RuntimeError(f"Pack v7 unexpectedly authorises {forbidden}.")

    print("Waypoint source-boundary classifier independent contract pack v7")
    print("=" * 78)
    print(f"Design-v4 SHA256:           {sha256(DESIGN_V4_PATH)}")
    print(f"Design-v4 review SHA256:    {sha256(DESIGN_V4_REVIEW_PATH)}")
    print(f"Pack-v6 rejection SHA256:   {sha256(PACK_V6_REVIEW_PATH)}")
    print()
    print("Construction isolation")
    print("-" * 78)
    print("Pack-v5 read:               NO")
    print("Pack-v6 read:               NO")
    print("Prior predictions read:     NO")
    print("Prior scores read:          NO")
    print("Failure analysis read:      NO")
    print("Prior case-ID namespaces:   NONE")
    print("Model calls:                NONE")
    print()
    print("Pack structure")
    print("-" * 78)
    print("Cases:                      50")
    print("Resolved cases:             44")
    print("Unresolved cases:           6")
    print("Source classes:             12/12")
    print("Resolved cases/class:       4 each")
    print("Contrast groups:            14")
    print("Contrast groups multi-class:14/14")
    print()
    print("Design-v4 coverage")
    print("-" * 78)
    print("All 3 context gates:        YES")
    print("Foreign issuer boundary:    YES")
    print("External agency boundary:   YES")
    print("Non-gated semantic cases:   YES")
    print("Unresolved ambiguity:       YES")
    print()
    print("Pack-v7 human review:       AUTHORISED")
    print("Threshold-v3 construction:  NOT AUTHORISED")
    print("Prompt-v3 construction:     NOT AUTHORISED")
    print("Implementation-v3:          NOT AUTHORISED")
    print("Blind-input-v3:             NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print()
    print("Next task:                  PACK-V7 HUMAN REVIEW")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Pack-v7 SHA256:             {sha256(OUTPUT_PATH)}")
    print()
    print("Runtime files modified:     NONE")
    print()
    print("Independent contract pack v7 freeze: PASS")


if __name__ == "__main__":
    main()
