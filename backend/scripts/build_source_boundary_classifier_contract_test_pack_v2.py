"""Build and freeze Waypoint source-boundary classifier contract test pack v2.

This pack is synthetic and derived only from the frozen classifier design v2.
It does not read retired external benchmarks, gold files, predictions, failure
taxonomies, or the v1 contract test pack.

Run from backend/:
    uv run python -m py_compile scripts/build_source_boundary_classifier_contract_test_pack_v2.py
    uv run python -m scripts.build_source_boundary_classifier_contract_test_pack_v2

Output:
    tests/source_boundary_classifier_contract_test_pack_v2.json
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

DESIGN_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v2.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v2.json"
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
            "Refusing to build contract test pack v2."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def resolved(
    *,
    test_id: str,
    proposition: str,
    source_domain: str,
    source_class: str,
    responsible_authority_type: str,
    basis: str,
    contrast_group: str | None = None,
    trusted_source_context: dict | None = None,
) -> dict:
    return {
        "test_id": test_id,
        "unsupported_proposition": proposition,
        "trusted_source_context": trusted_source_context,
        "expected": {
            "resolution_status": "resolved",
            "source_domain": source_domain,
            "source_class": source_class,
            "responsible_authority_type": responsible_authority_type,
        },
        "basis": basis,
        "contrast_group": contrast_group,
    }


def unresolved(
    *,
    test_id: str,
    proposition: str,
    basis: str,
    contrast_group: str | None = None,
    trusted_source_context: dict | None = None,
) -> dict:
    return {
        "test_id": test_id,
        "unsupported_proposition": proposition,
        "trusted_source_context": trusted_source_context,
        "expected": {
            "resolution_status": "unresolved",
            "source_domain": "unresolved",
            "source_class": "unresolved",
            "responsible_authority_type": "unresolved",
        },
        "basis": basis,
        "contrast_group": contrast_group,
    }


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Contract test pack v2 already exists: {OUTPUT_PATH}\n"
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
        "Frozen source-boundary classifier design v2",
    )

    design = load_json(DESIGN_V2_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v2"
    ):
        raise RuntimeError("Unexpected classifier design-v2 schema.")

    if design.get("status") != (
        "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError("Unexpected classifier design-v2 status.")

    authorisations = design.get("authorisations", {})

    if authorisations.get(
        "contract_test_pack_v2_build_authorised"
    ) is not True:
        raise RuntimeError(
            "Classifier design v2 does not authorise test-pack v2 build."
        )

    for forbidden_authorisation in (
        "classifier_model_prediction_authorised",
        "classifier_experimental_implementation_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if authorisations.get(forbidden_authorisation) is not False:
            raise RuntimeError(
                "Classifier design v2 unexpectedly authorises: "
                f"{forbidden_authorisation}"
            )

    tests = [
        resolved(
            test_id="sbv2_01",
            proposition=(
                "Whether the conditions attached to a temporary visa permit "
                "the holder to perform self-employed work."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is itself a visa-condition rule."
            ),
            contrast_group="manual_rule_vs_live_service",
        ),
        resolved(
            test_id="sbv2_02",
            proposition=(
                "Whether an applicant must provide a specified type of "
                "document to satisfy an immigration evidential requirement."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration evidence requirement."
            ),
            contrast_group="inz_requirement_vs_foreign_procedure",
        ),
        resolved(
            test_id="sbv2_03",
            proposition=(
                "Whether an immigration exception removes a person from an "
                "otherwise applicable visa criterion."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration exception rule."
            ),
            contrast_group="manual_rule_vs_nonmanual_procedure",
        ),
        resolved(
            test_id="sbv2_04",
            proposition=(
                "Whether an immigration health criterion must be met before "
                "a visa can be granted."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration decision criterion."
            ),
            contrast_group="immigration_health_vs_public_entitlement",
        ),
        resolved(
            test_id="sbv2_05",
            proposition=(
                "Whether a newly certified immigration requirement applies "
                "before the local indexed Manual has been refreshed."
            ),
            source_domain="certified_immigration_instructions",
            source_class="manual_instruction_transition",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "Trusted context establishes a certified amendment that has "
                "not yet been incorporated into the local index."
            ),
            contrast_group="transition_context_required",
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "certified_amendment",
                "authority_role": "immigration_instruction_owner",
                "certification_status": "certified",
                "incorporation_status": "not_yet_indexed",
            },
        ),
        resolved(
            test_id="sbv2_06",
            proposition=(
                "Whether a certified amendment changes an immigration "
                "condition while the local indexed Manual still contains "
                "older wording."
            ),
            source_domain="certified_immigration_instructions",
            source_class="manual_instruction_transition",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "Trusted context establishes a certified amendment and a "
                "stale local index."
            ),
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "certified_amendment",
                "authority_role": "immigration_instruction_owner",
                "certification_status": "certified",
                "incorporation_status": "stale_local_index",
            },
        ),
        resolved(
            test_id="sbv2_07",
            proposition=(
                "Whether legislation gives a Minister the legal authority to "
                "certify immigration instructions."
            ),
            source_domain="legislation_or_regulation",
            source_class="legislation_or_regulation",
            responsible_authority_type="new_zealand_legislation",
            basis=(
                "The proposition concerns statutory authority."
            ),
            contrast_group="legal_authority_vs_instruction_content",
        ),
        resolved(
            test_id="sbv2_08",
            proposition=(
                "Whether a particular application formality is prescribed "
                "directly by immigration regulations."
            ),
            source_domain="legislation_or_regulation",
            source_class="legislation_or_regulation",
            responsible_authority_type="new_zealand_legislation",
            basis=(
                "The proposition is expressly regulatory rather than an "
                "immigration-instruction criterion."
            ),
        ),
        resolved(
            test_id="sbv2_09",
            proposition=(
                "Whether regulations provide the legal basis for imposing an "
                "immigration levy."
            ),
            source_domain="legislation_or_regulation",
            source_class="legislation_or_regulation",
            responsible_authority_type="new_zealand_legislation",
            basis=(
                "The proposition concerns the legal basis for a charge."
            ),
            contrast_group="fee_legal_basis_vs_current_amount",
        ),
        resolved(
            test_id="sbv2_10",
            proposition=(
                "The current processing timeframe displayed by Immigration "
                "New Zealand for a visa service."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_live_service_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is a current, time-varying INZ service value."
            ),
            contrast_group="manual_rule_vs_live_service",
        ),
        resolved(
            test_id="sbv2_11",
            proposition=(
                "Whether a particular Immigration New Zealand application "
                "channel is accepting submissions at the present time."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_live_service_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is current operational channel availability."
            ),
        ),
        resolved(
            test_id="sbv2_12",
            proposition=(
                "Whether places are currently available in a capped "
                "Immigration New Zealand application service."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_live_service_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is a current operational availability state."
            ),
        ),
        resolved(
            test_id="sbv2_13",
            proposition=(
                "The amount an applicant would currently pay to submit a visa "
                "application from a specified location."
            ),
            source_domain="official_inz_non_manual",
            source_class="current_fee_or_charge_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition asks for the current payable amount."
            ),
            contrast_group="fee_legal_basis_vs_current_amount",
        ),
        resolved(
            test_id="sbv2_14",
            proposition=(
                "The current levy amount included in an immigration "
                "application charge."
            ),
            source_domain="official_inz_non_manual",
            source_class="current_fee_or_charge_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition concerns a current charge value."
            ),
        ),
        resolved(
            test_id="sbv2_15",
            proposition=(
                "Which administrative step Immigration New Zealand staff "
                "follow when transferring an application between offices."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_non_manual_procedure_or_interpretation",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "Trusted context identifies an Internal Administration "
                "Circular as the source that owns this procedure."
            ),
            contrast_group="inz_nonmanual_context_required",
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "inz_iac",
                "authority_role": "immigration_instruction_owner",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        resolved(
            test_id="sbv2_16",
            proposition=(
                "How Immigration New Zealand staff are instructed to apply an "
                "operational interpretation in a non-Manual staff publication."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_non_manual_procedure_or_interpretation",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "Trusted context identifies Advice to Staff as the owning "
                "non-Manual publication family."
            ),
            contrast_group="manual_rule_vs_nonmanual_procedure",
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "inz_advice_to_staff",
                "authority_role": "immigration_instruction_owner",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        resolved(
            test_id="sbv2_17",
            proposition=(
                "Which option a foreign police authority requires an "
                "applicant to choose on that authority's own clearance "
                "request form."
            ),
            source_domain="responsible_external_official_authority",
            source_class="foreign_issuing_authority_procedure",
            responsible_authority_type="foreign_issuing_authority",
            basis=(
                "The proposition concerns the foreign authority's own "
                "document-issuing procedure."
            ),
            contrast_group="inz_requirement_vs_foreign_procedure",
        ),
        resolved(
            test_id="sbv2_18",
            proposition=(
                "How a foreign government office requires identity material "
                "to be submitted when requesting one of its official "
                "certificates."
            ),
            source_domain="responsible_external_official_authority",
            source_class="foreign_issuing_authority_procedure",
            responsible_authority_type="foreign_issuing_authority",
            basis=(
                "The foreign issuing authority owns the application procedure."
            ),
        ),
        resolved(
            test_id="sbv2_19",
            proposition=(
                "Which qualification-recognition service a non-professional "
                "New Zealand statutory agency provides for an overseas "
                "credential assessment."
            ),
            source_domain="responsible_external_official_authority",
            source_class="external_agency_assessment_or_service",
            responsible_authority_type="new_zealand_external_agency",
            basis=(
                "The proposition concerns a non-professional statutory "
                "agency's recognition service."
            ),
            contrast_group="agency_vs_professional_assessment",
            trusted_source_context={
                "publisher_family": "new_zealand_external_agency",
                "publication_family": "external_agency_service",
                "authority_role": "non_professional_agency_assessment",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        resolved(
            test_id="sbv2_20",
            proposition=(
                "How a non-professional government agency assesses an "
                "overseas credential submitted to its recognition service."
            ),
            source_domain="responsible_external_official_authority",
            source_class="external_agency_assessment_or_service",
            responsible_authority_type="new_zealand_external_agency",
            basis=(
                "The proposition belongs to a non-professional agency "
                "assessment process."
            ),
            trusted_source_context={
                "publisher_family": "new_zealand_external_agency",
                "publication_family": "external_agency_service",
                "authority_role": "non_professional_agency_assessment",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        resolved(
            test_id="sbv2_21",
            proposition=(
                "Whether a person qualifies for publicly funded health "
                "services under the health system's own eligibility regime."
            ),
            source_domain="responsible_external_official_authority",
            source_class="external_entitlement_or_service_regime",
            responsible_authority_type="public_service_authority",
            basis=(
                "The proposition is a public-service entitlement decision."
            ),
            contrast_group="immigration_health_vs_public_entitlement",
        ),
        resolved(
            test_id="sbv2_22",
            proposition=(
                "Whether a person is eligible for a separately administered "
                "public benefit because of their current status."
            ),
            source_domain="responsible_external_official_authority",
            source_class="external_entitlement_or_service_regime",
            responsible_authority_type="public_service_authority",
            basis=(
                "The responsible public-service authority owns the "
                "entitlement proposition."
            ),
        ),
        resolved(
            test_id="sbv2_23",
            proposition=(
                "Which evidence a professional registration authority "
                "requires before assessing a person's registration."
            ),
            source_domain="responsible_external_official_authority",
            source_class="professional_or_assessor_guidance",
            responsible_authority_type="professional_or_assessment_authority",
            basis=(
                "Professional registration falls within the professional "
                "authority class and takes precedence over the generic agency "
                "assessment class."
            ),
            contrast_group="agency_vs_professional_assessment",
            trusted_source_context={
                "publisher_family": "professional_or_assessment_authority",
                "publication_family": "professional_or_assessment_service",
                "authority_role": "professional_registration",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        resolved(
            test_id="sbv2_24",
            proposition=(
                "Whether a clinical assessor requires a specialist report "
                "before completing the assessor's own evaluation."
            ),
            source_domain="responsible_external_official_authority",
            source_class="professional_or_assessor_guidance",
            responsible_authority_type="professional_or_assessment_authority",
            basis=(
                "The proposition is owned by a clinical assessment authority."
            ),
            contrast_group="clinical_assessor_vs_public_entitlement",
            trusted_source_context={
                "publisher_family": "professional_or_assessment_authority",
                "publication_family": "professional_or_assessment_service",
                "authority_role": "clinical_assessment",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        resolved(
            test_id="sbv2_25",
            proposition=(
                "How a professional assessment body evaluates a practitioner "
                "against its own competency framework."
            ),
            source_domain="responsible_external_official_authority",
            source_class="professional_or_assessor_guidance",
            responsible_authority_type="professional_or_assessment_authority",
            basis=(
                "The authority role is explicitly professional assessment."
            ),
            trusted_source_context={
                "publisher_family": "professional_or_assessment_authority",
                "publication_family": "professional_or_assessment_service",
                "authority_role": "professional_assessment",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        resolved(
            test_id="sbv2_26",
            proposition=(
                "Which electronic declaration channel a foreign customs "
                "authority requires travellers to use for its own customs "
                "reporting process."
            ),
            source_domain="responsible_external_official_authority",
            source_class="other_official_external_authority",
            responsible_authority_type="other_official_authority",
            basis=(
                "Trusted context identifies an official foreign operational "
                "owner. The proposition is not a document-issuing procedure, "
                "professional assessment, agency recognition service, public "
                "entitlement, or legislation proposition."
            ),
            contrast_group="other_official_context_required",
            trusted_source_context={
                "publisher_family": "other_official_authority",
                "publication_family": "other_official_service",
                "authority_role": "other_official_operational_owner",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        resolved(
            test_id="sbv2_27",
            proposition=(
                "Which operational notification channel a foreign transport "
                "authority requires operators to use for an administrative "
                "report that is not a licensing, registration, entitlement, "
                "recognition, or document-issuing process."
            ),
            source_domain="responsible_external_official_authority",
            source_class="other_official_external_authority",
            responsible_authority_type="other_official_authority",
            basis=(
                "Trusted context identifies an official operational owner and "
                "the proposition explicitly excludes the more specific frozen "
                "external source classes."
            ),
            trusted_source_context={
                "publisher_family": "other_official_authority",
                "publication_family": "other_official_service",
                "authority_role": "other_official_operational_owner",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        unresolved(
            test_id="sbv2_28",
            proposition=(
                "Whether a recently announced immigration change will apply "
                "to a future application, where no trusted source metadata "
                "shows whether it is certified instructions, legislation, or "
                "non-binding guidance."
            ),
            basis=(
                "Recency wording alone cannot establish authoritative source "
                "location."
            ),
            contrast_group="transition_context_required",
        ),
        unresolved(
            test_id="sbv2_29",
            proposition=(
                "Which internal processing step Immigration New Zealand staff "
                "follow when moving an application between offices, where no "
                "trusted source metadata identifies whether the procedure is "
                "in certified instructions or a non-Manual publication."
            ),
            basis=(
                "Procedural semantics alone cannot establish an INZ "
                "non-Manual source location."
            ),
            contrast_group="inz_nonmanual_context_required",
        ),
        unresolved(
            test_id="sbv2_30",
            proposition=(
                "Which operational channel an unnamed foreign authority "
                "requires for an administrative report, where the authority "
                "type and source family are not identified."
            ),
            basis=(
                "Ownership cannot be established and the other-official class "
                "must not be used as an ambiguity catch-all."
            ),
            contrast_group="other_official_context_required",
        ),
        unresolved(
            test_id="sbv2_31",
            proposition=(
                "How an organisation assesses a person's credentials, where "
                "the proposition does not establish whether the organisation "
                "is a professional registration body or a non-professional "
                "government assessment agency."
            ),
            basis=(
                "The professional-versus-agency distinction cannot be safely "
                "resolved from the proposition."
            ),
            contrast_group=None,
        ),
        unresolved(
            test_id="sbv2_32",
            proposition=(
                "Whether an official rule described only as guidance is "
                "binding, where neither the publishing authority nor the "
                "publication family is identified."
            ),
            basis=(
                "The proposition does not distinguish certified instructions, "
                "legislation, non-Manual guidance, or another official source."
            ),
        ),
        unresolved(
            test_id="sbv2_33",
            proposition=(
                "Whether a requirement about medical information is owned by "
                "immigration instructions, a public-service entitlement "
                "authority, or a clinical assessor, where the proposition "
                "does not identify which decision is being made."
            ),
            basis=(
                "The decision owner and proposition type are materially "
                "ambiguous."
            ),
            contrast_group="clinical_assessor_vs_public_entitlement",
        ),
        resolved(
            test_id="sbv2_34",
            proposition=(
                "Whether certified immigration instructions require an "
                "applicant to meet a stated visa criterion."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition concerns the content of a certified "
                "immigration instruction rather than the legislation that "
                "authorises instructions to be made."
            ),
            contrast_group="legal_authority_vs_instruction_content",
        ),
    ]

    if len(tests) != 34:
        raise RuntimeError(
            f"Expected 34 synthetic contract tests, got {len(tests)}."
        )

    ids = [item["test_id"] for item in tests]

    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate synthetic test_id values.")

    if ids != [f"sbv2_{number:02d}" for number in range(1, 35)]:
        raise RuntimeError(
            "Synthetic test IDs are not the expected contiguous v2 sequence."
        )

    resolved_count = sum(
        item["expected"]["resolution_status"] == "resolved"
        for item in tests
    )
    unresolved_count = sum(
        item["expected"]["resolution_status"] == "unresolved"
        for item in tests
    )

    if (resolved_count, unresolved_count) != (28, 6):
        raise RuntimeError(
            "Unexpected resolved/unresolved v2 test distribution."
        )

    class_counts: dict[str, int] = {}

    for item in tests:
        source_class = item["expected"]["source_class"]
        class_counts[source_class] = (
            class_counts.get(source_class, 0) + 1
        )

    required_classes = {
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
    }

    if set(class_counts) != required_classes:
        raise RuntimeError(
            "Contract test pack v2 does not cover every frozen source class."
        )

    for source_class in required_classes - {"unresolved"}:
        if class_counts.get(source_class, 0) < 2:
            raise RuntimeError(
                f"Resolved source class has fewer than two tests: "
                f"{source_class}"
            )

    if class_counts.get("unresolved") != 6:
        raise RuntimeError("Expected exactly 6 unresolved tests.")

    context_required_classes = {
        "manual_instruction_transition",
        "inz_non_manual_procedure_or_interpretation",
        "other_official_external_authority",
    }

    for item in tests:
        source_class = item["expected"]["source_class"]

        if source_class in context_required_classes:
            if not isinstance(item.get("trusted_source_context"), dict):
                raise RuntimeError(
                    f"{item['test_id']}: {source_class} requires trusted "
                    "source context."
                )

    contrast_groups: dict[str, list[str]] = {}

    for item in tests:
        group = item.get("contrast_group")
        if group:
            contrast_groups.setdefault(group, []).append(item["test_id"])

    required_contrast_groups = {
        "manual_rule_vs_live_service",
        "inz_requirement_vs_foreign_procedure",
        "manual_rule_vs_nonmanual_procedure",
        "immigration_health_vs_public_entitlement",
        "transition_context_required",
        "legal_authority_vs_instruction_content",
        "fee_legal_basis_vs_current_amount",
        "inz_nonmanual_context_required",
        "agency_vs_professional_assessment",
        "clinical_assessor_vs_public_entitlement",
        "other_official_context_required",
    }

    if set(contrast_groups) != required_contrast_groups:
        raise RuntimeError(
            "Unexpected contract test-pack v2 contrast-group set."
        )

    singleton_groups = {
        group: members
        for group, members in contrast_groups.items()
        if len(members) < 2
    }

    if singleton_groups:
        raise RuntimeError(
            "Every frozen contrast group must have at least two tests. "
            f"Singleton groups: {singleton_groups}"
        )

    pack = {
        "schema": (
            "waypoint-source-boundary-classifier-contract-test-pack-v2"
        ),
        "status": (
            "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_NO_MODEL_RUN"
        ),
        "frozen_on": str(date.today()),
        "construction": {
            "basis": (
                "Synthetic unsupported propositions derived only from frozen "
                "source-boundary classifier design v2."
            ),
            "classifier_design_v2_sha256": EXPECTED_DESIGN_V2_SHA256,
            "retired_external_benchmark_questions_read": False,
            "gold_files_read": False,
            "prediction_files_read": False,
            "failure_taxonomy_read": False,
            "contract_test_pack_v1_read": False,
            "model_generated": False,
            "test_count": len(tests),
            "resolved_count": resolved_count,
            "unresolved_count": unresolved_count,
        },
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "classifier_design_v2_sha256": EXPECTED_DESIGN_V2_SHA256,
        },
        "coverage": {
            "source_class_counts": class_counts,
            "contrast_groups": contrast_groups,
            "context_required_classes": sorted(
                context_required_classes
            ),
        },
        "scoring_contract": {
            "primary_metric": {
                "name": "four_field_exact_match_accuracy",
                "fields": [
                    "resolution_status",
                    "source_domain",
                    "source_class",
                    "responsible_authority_type",
                ],
                "case_is_correct_only_if_all_fields_match": True,
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
            "required_confusions": [
                "resolution_status_confusion",
                "source_domain_confusion",
                "source_class_confusion",
            ],
            "basis_text_scoring": "diagnostic_only_not_exact_match",
            "malformed_output": "incorrect",
            "classifier_error": "incorrect",
            "automatic_retry": False,
            "acceptance_thresholds_frozen": False,
            "model_prediction_authorised": False,
        },
        "tests": tests,
        "authorisations": {
            "contract_test_pack_v2_frozen": True,
            "human_review_v2_authorised": True,
            "acceptance_threshold_freeze_authorised": False,
            "classifier_model_prediction_authorised": False,
            "classifier_experimental_implementation_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_step": {
            "name": "human_review_contract_test_pack_v2",
            "authorised": True,
            "purpose": (
                "Review every v2 synthetic proposition and expected source "
                "ownership for ambiguity, context sufficiency, exclusivity, "
                "and contrast quality before freezing classifier acceptance "
                "thresholds."
            ),
        },
    }

    serialised = json.dumps(
        pack,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    forbidden_exact_keys = (
        "expected_sections",
        "candidate_id",
        "case_id",
        "adjudication_note",
        "benchmark_status",
        "expected_answer",
    )

    for key in forbidden_exact_keys:
        if re.search(
            rf'"{re.escape(key)}"\s*:',
            serialised,
            flags=re.IGNORECASE,
        ):
            raise RuntimeError(
                f"Forbidden benchmark/evaluation field in v2 pack: {key}"
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
            "Forbidden retired benchmark IDs in v2 test pack: "
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
        "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_NO_MODEL_RUN"
    ):
        raise RuntimeError("Saved v2 test-pack status changed.")

    saved_auth = saved.get("authorisations", {})

    if saved_auth.get("human_review_v2_authorised") is not True:
        raise RuntimeError(
            "Saved v2 test pack does not authorise human review."
        )

    for forbidden_authorisation in (
        "acceptance_threshold_freeze_authorised",
        "classifier_model_prediction_authorised",
        "classifier_experimental_implementation_authorised",
        "classifier_runtime_implementation_authorised",
        "candidate_v7_build_authorised",
        "production_runtime_change_authorised",
        "external_source_retrieval_authorised",
        "fresh_external_v3_holdout_authorised",
    ):
        if saved_auth.get(forbidden_authorisation) is not False:
            raise RuntimeError(
                "V2 test pack unexpectedly authorises: "
                f"{forbidden_authorisation}"
            )

    print("Waypoint source-boundary classifier contract test-pack-v2 freeze")
    print("=" * 64)
    print(f"Production v2 SHA256:        {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:        {sha256(BOUNDARY_PATH)}")
    print(f"Classifier design-v2 SHA:    {sha256(DESIGN_V2_PATH)}")
    print()
    print("Construction basis:          SYNTHETIC DESIGN V2")
    print("Retired benchmark read:      NO")
    print("Gold files read:             NO")
    print("Prediction files read:       NO")
    print("Failure taxonomy read:       NO")
    print("Contract pack v1 read:       NO")
    print()
    print(f"Synthetic tests:             {len(tests)}")
    print(f"Resolved expected:           {resolved_count}")
    print(f"Unresolved expected:         {unresolved_count}")
    print(f"Source classes covered:      {len(class_counts)}")
    print(f"Contrast groups:             {len(contrast_groups)}")
    print()
    print("Design-v2 ambiguity controls")
    print("-" * 64)
    print("Transition source context:   TESTED")
    print("INZ non-Manual context:      TESTED")
    print("Agency vs professional:      TESTED")
    print("Other-official last resort:  TESTED")
    print("Explicit unresolved cases:   TESTED")
    print()
    print("Scoring contract")
    print("-" * 64)
    print("4-field exact match:         REQUIRED")
    print("Source-class macro recall:   REQUIRED")
    print("Per-class recall:            REQUIRED")
    print("Resolved/unresolved recall:  REQUIRED")
    print("Contrast consistency:        REQUIRED")
    print("Malformed/error rate:        REQUIRED")
    print("Automatic retry:             NO")
    print()
    print("Acceptance thresholds:       NOT YET FROZEN")
    print("Classifier model prediction: NOT AUTHORISED")
    print("Classifier implementation:   NOT AUTHORISED")
    print("Candidate v7 build:          NOT AUTHORISED")
    print("Production change:           NOT AUTHORISED")
    print("Fresh external-v3:           NOT AUTHORISED")
    print()
    print("Next step:                   HUMAN REVIEW OF V2 TEST PACK")
    print()
    print(f"Output:                      {OUTPUT_PATH}")
    print(f"Test-pack-v2 SHA256:         {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                 NONE")
    print("Retrieval/reranker calls:    NONE")
    print("Database writes:             NONE")
    print("Runtime files modified:      NONE")
    print()
    print("Source-boundary contract test-pack-v2 freeze: PASS")


if __name__ == "__main__":
    main()
