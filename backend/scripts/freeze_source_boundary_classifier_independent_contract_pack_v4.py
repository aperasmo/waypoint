"""Freeze an independent synthetic contract pack v4 for classifier design v3.

PACK CONSTRUCTION ONLY.
- No model calls.
- Does not read the observed v3 contract pack.
- Does not read predictions, scores, failure analysis, or observed case IDs.
- Does not authorise implementation or prediction.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_independent_contract_pack_v4.py
    uv run python -m scripts.freeze_source_boundary_classifier_independent_contract_pack_v4

Output:
    tests/source_boundary_classifier_independent_contract_test_pack_v4.json
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
    BACKEND_DIR / "app" / "api" / "routes" / "ask.py"
)

BOUNDARY_PATH = (
    BACKEND_DIR
    / "tests"
    / "authoritative_source_boundary_spec_v1.json"
)

DESIGN_V3_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v3.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_independent_contract_test_pack_v4.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_BOUNDARY_SHA256 = (
    "2BFC518CFD892FE54AD9E46EAEE0037A9"
    "05730DDA934E3EEAEB1EBAD42C1458F"
)

EXPECTED_DESIGN_V3_SHA256 = (
    "0EFBA11ECA5EE07A41BBB841817B93CB4"
    "69BFA5B48BF42DF268B6A8F3257356B"
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

EXPECTED_DERIVATION = {
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
            "Refusing to freeze independent contract pack v4."
        )


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: root must be a JSON object."
        )

    return payload


def expected_for(source_class: str) -> dict[str, str]:
    derived = EXPECTED_DERIVATION[source_class]

    return {
        "resolution_status": derived["resolution_status"],
        "source_domain": derived["source_domain"],
        "source_class": source_class,
        "responsible_authority_type": (
            derived["responsible_authority_type"]
        ),
    }


def case(
    case_id: str,
    proposition: str,
    source_class: str,
    basis: str,
    *,
    trusted_source_context: dict[str, str] | None = None,
    contrast_group: str | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "unsupported_proposition": proposition,
        "trusted_source_context": trusted_source_context,
        "expected": expected_for(source_class),
        "basis": basis,
        "contrast_group": contrast_group,
    }


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Independent contract pack already exists: {OUTPUT_PATH}\n"
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
        DESIGN_V3_PATH,
        EXPECTED_DESIGN_V3_SHA256,
        "Frozen classifier design v3",
    )

    design = load_json(DESIGN_V3_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v3"
    ):
        raise RuntimeError("Unexpected design-v3 schema.")

    if design.get("status") != (
        "FROZEN_REVISED_DESIGN_READY_FOR_INDEPENDENT_PACK_CONSTRUCTION"
    ):
        raise RuntimeError(
            "Design v3 is not frozen for independent pack construction."
        )

    if design.get(
        "authorisations",
        {},
    ).get(
        "new_independent_acceptance_pack_construction_authorised"
    ) is not True:
        raise RuntimeError(
            "Design v3 does not authorise independent pack construction."
        )

    model_classes = (
        design.get("model_output_contract", {})
        .get("fields", {})
        .get("source_class", {})
        .get("allowed_values")
    )

    if model_classes != SOURCE_CLASSES:
        raise RuntimeError(
            "Design-v3 source-class taxonomy changed."
        )

    if design.get(
        "deterministic_derivation"
    ) != EXPECTED_DERIVATION:
        raise RuntimeError(
            "Design-v3 deterministic derivation changed."
        )

    tests = [
        # operational_manual_instruction
        case(
            "iv4_001",
            (
                "Whether a visa holder must satisfy an ongoing condition "
                "specified by immigration instructions before changing employer."
            ),
            "operational_manual_instruction",
            (
                "This is a substantive immigration-instruction condition, not "
                "a live service value or external procedure."
            ),
            contrast_group="instruction_rule_vs_live_status",
        ),
        case(
            "iv4_002",
            (
                "Whether a dependent child may be included when an immigration "
                "instruction sets an age and dependency requirement."
            ),
            "operational_manual_instruction",
            (
                "The proposition concerns an eligibility requirement created "
                "by certified immigration instructions."
            ),
        ),
        case(
            "iv4_003",
            (
                "Whether an applicant can be exempted from a normally required "
                "immigration criterion under an instruction-defined exception."
            ),
            "operational_manual_instruction",
            (
                "An exception to an immigration criterion is instruction-rule "
                "content."
            ),
            contrast_group="instruction_exception_vs_nonmanual_guidance",
        ),
        case(
            "iv4_004",
            (
                "Whether immigration instructions require a minimum period of "
                "qualifying employment before a residence pathway can be used."
            ),
            "operational_manual_instruction",
            (
                "The proposition asks for a certified immigration eligibility "
                "rule."
            ),
            contrast_group="instruction_rule_vs_statutory_authority",
        ),

        # manual_instruction_transition
        case(
            "iv4_005",
            (
                "Whether a newly certified immigration amendment applies before "
                "the local Operational Manual index has incorporated it."
            ),
            "manual_instruction_transition",
            (
                "Trusted amendment metadata establishes a certified instruction "
                "transition not yet incorporated into the local index."
            ),
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "certified_amendment",
                "authority_role": "immigration_instruction_owner",
                "certification_status": "certified",
                "incorporation_status": "not_yet_indexed",
            },
            contrast_group="certified_transition_vs_unverified_change",
        ),
        case(
            "iv4_006",
            (
                "Which certified amendment controls where the indexed Manual "
                "still contains the superseded wording."
            ),
            "manual_instruction_transition",
            (
                "Trusted context identifies a certified amendment and a stale "
                "local index."
            ),
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "certified_amendment",
                "authority_role": "immigration_instruction_owner",
                "certification_status": "certified",
                "incorporation_status": "stale_local_index",
            },
        ),
        case(
            "iv4_007",
            (
                "Whether a certified instruction change is already controlling "
                "even though the local corpus has not yet been refreshed."
            ),
            "manual_instruction_transition",
            (
                "This is a certified transition scenario established by trusted "
                "amendment and incorporation metadata."
            ),
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "certified_amendment",
                "authority_role": "immigration_instruction_owner",
                "certification_status": "certified",
                "incorporation_status": "not_yet_indexed",
            },
        ),

        # legislation_or_regulation
        case(
            "iv4_008",
            (
                "Which statutory provision gives immigration officers the legal "
                "power to require specified information."
            ),
            "legislation_or_regulation",
            (
                "The proposition asks for legal authority, not operational "
                "instruction content."
            ),
            contrast_group="instruction_rule_vs_statutory_authority",
        ),
        case(
            "iv4_009",
            (
                "Whether regulations legally authorise the imposition of an "
                "immigration-related levy."
            ),
            "legislation_or_regulation",
            (
                "The proposition concerns the legal basis of a charge rather "
                "than its current payable amount."
            ),
            contrast_group="legal_charge_basis_vs_current_charge",
        ),
        case(
            "iv4_010",
            (
                "Whether an enactment permits information sharing between "
                "Immigration New Zealand and another public agency."
            ),
            "legislation_or_regulation",
            (
                "This asks for statutory or regulatory authority."
            ),
        ),

        # inz_live_service_information
        case(
            "iv4_011",
            (
                "How long Immigration New Zealand is presently estimating for "
                "most applications in a named visa category."
            ),
            "inz_live_service_information",
            (
                "A current processing estimate is a time-varying INZ service "
                "value."
            ),
            contrast_group="instruction_rule_vs_live_status",
        ),
        case(
            "iv4_012",
            (
                "Whether an Immigration New Zealand online submission portal is "
                "open for new applications today."
            ),
            "inz_live_service_information",
            (
                "The proposition concerns current operational availability of "
                "an INZ service channel."
            ),
            contrast_group="current_charge_vs_live_nonprice_status",
        ),
        case(
            "iv4_013",
            (
                "Whether the remaining quota for a capped Immigration New "
                "Zealand application category is currently exhausted."
            ),
            "inz_live_service_information",
            (
                "Current quota/service availability is live operational "
                "information."
            ),
        ),
        case(
            "iv4_014",
            (
                "What appointment slots Immigration New Zealand is currently "
                "showing for a service centre."
            ),
            "inz_live_service_information",
            (
                "Current appointment availability is a live INZ service state."
            ),
            contrast_group="live_service_vs_nonmanual_publication",
        ),

        # current_fee_or_charge_information
        case(
            "iv4_015",
            (
                "What total application charge is payable today for a visa "
                "lodged from a particular country."
            ),
            "current_fee_or_charge_information",
            (
                "The proposition asks for the current payable immigration "
                "charge."
            ),
            contrast_group="legal_charge_basis_vs_current_charge",
        ),
        case(
            "iv4_016",
            (
                "What immigration levy amount is included in the fee currently "
                "charged for a specified application type."
            ),
            "current_fee_or_charge_information",
            (
                "This asks for the present value of an immigration charge."
            ),
        ),
        case(
            "iv4_017",
            (
                "What additional service fee an applicant currently pays when "
                "using a specified Immigration New Zealand application channel."
            ),
            "current_fee_or_charge_information",
            (
                "A present channel-specific payable amount belongs to current "
                "fee/charge information."
            ),
            contrast_group="current_charge_vs_live_nonprice_status",
        ),

        # inz_non_manual_procedure_or_interpretation
        case(
            "iv4_018",
            (
                "How an Immigration New Zealand internal administration circular "
                "instructs staff to handle a particular processing situation."
            ),
            "inz_non_manual_procedure_or_interpretation",
            (
                "Trusted publication context identifies an INZ IAC rather than "
                "certified Manual content."
            ),
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "inz_iac",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
            contrast_group="instruction_exception_vs_nonmanual_guidance",
        ),
        case(
            "iv4_019",
            (
                "What an Immigration New Zealand Advice to Staff publication "
                "says about applying an operational procedure."
            ),
            "inz_non_manual_procedure_or_interpretation",
            (
                "Trusted metadata identifies an Advice to Staff publication."
            ),
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "inz_advice_to_staff",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),
        case(
            "iv4_020",
            (
                "Which steps an official Immigration New Zealand form guide "
                "directs applicants to follow when supplying supporting material."
            ),
            "inz_non_manual_procedure_or_interpretation",
            (
                "Trusted context establishes an INZ form/guide publication."
            ),
            trusted_source_context={
                "publisher_family": "immigration_new_zealand",
                "publication_family": "inz_form_or_guide",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
            contrast_group="live_service_vs_nonmanual_publication",
        ),

        # foreign_issuing_authority_procedure
        case(
            "iv4_021",
            (
                "How a foreign civil registry requires a person to request a "
                "replacement birth certificate from that registry."
            ),
            "foreign_issuing_authority_procedure",
            (
                "The foreign authority is acting in the role of issuer of the "
                "requested civil record."
            ),
            contrast_group="foreign_issuing_vs_general_foreign_operation",
        ),
        case(
            "iv4_022",
            (
                "What procedure a foreign police records office uses to issue "
                "an official police clearance certificate."
            ),
            "foreign_issuing_authority_procedure",
            (
                "The proposition concerns obtaining a record from the foreign "
                "authority that issues it."
            ),
        ),
        case(
            "iv4_023",
            (
                "How a foreign passport authority requires a damaged passport "
                "to be replaced."
            ),
            "foreign_issuing_authority_procedure",
            (
                "The responsible foreign authority is acting in a document-"
                "issuing role."
            ),
            contrast_group="foreign_issuing_vs_external_agency_service",
        ),

        # external_agency_assessment_or_service
        case(
            "iv4_024",
            (
                "How a New Zealand government qualifications agency assesses "
                "whether an overseas qualification is comparable to a local one."
            ),
            "external_agency_assessment_or_service",
            (
                "This is a non-professional external government assessment "
                "service."
            ),
            contrast_group="agency_assessment_vs_professional_assessment",
        ),
        case(
            "iv4_025",
            (
                "How an external government identity agency verifies an official "
                "identity record through its own service."
            ),
            "external_agency_assessment_or_service",
            (
                "The proposition concerns an administrative service owned by "
                "another official government agency."
            ),
        ),
        case(
            "iv4_026",
            (
                "Which verification service a public records agency provides to "
                "confirm the authenticity of a document already issued."
            ),
            "external_agency_assessment_or_service",
            (
                "The agency is providing a verification service rather than "
                "acting as the issuing authority for the requested document."
            ),
            contrast_group="foreign_issuing_vs_external_agency_service",
        ),

        # external_entitlement_or_service_regime
        case(
            "iv4_027",
            (
                "Whether a person's immigration status makes them eligible for "
                "a publicly funded health service administered outside INZ."
            ),
            "external_entitlement_or_service_regime",
            (
                "This is an eligibility question within a separately "
                "administered public-service regime."
            ),
            contrast_group="immigration_status_rule_vs_external_entitlement",
        ),
        case(
            "iv4_028",
            (
                "Whether a temporary resident can access a government education "
                "subsidy administered by the education authority."
            ),
            "external_entitlement_or_service_regime",
            (
                "The authoritative home is the external public-service "
                "entitlement regime."
            ),
        ),
        case(
            "iv4_029",
            (
                "Whether a person's current visa status qualifies them for a "
                "public housing service administered by another agency."
            ),
            "external_entitlement_or_service_regime",
            (
                "The proposition is about access to a separately administered "
                "public benefit."
            ),
            contrast_group="immigration_status_rule_vs_external_entitlement",
        ),

        # professional_or_assessor_guidance
        case(
            "iv4_030",
            (
                "Which evidence a professional registration body requires when "
                "assessing overseas professional competence."
            ),
            "professional_or_assessor_guidance",
            (
                "The authoritative owner is a professional registration body."
            ),
            contrast_group="agency_assessment_vs_professional_assessment",
        ),
        case(
            "iv4_031",
            (
                "What clinical criteria an authorised medical assessor applies "
                "when completing a specialist fitness assessment."
            ),
            "professional_or_assessor_guidance",
            (
                "The proposition belongs to a clinical/specialist assessor "
                "authority."
            ),
        ),
        case(
            "iv4_032",
            (
                "What standards an approved professional assessor uses to "
                "evaluate occupational competence."
            ),
            "professional_or_assessor_guidance",
            (
                "The authoritative home is a professional assessment role."
            ),
        ),

        # other_official_external_authority
        case(
            "iv4_033",
            (
                "Which electronic arrival declaration system a foreign border "
                "authority requires travellers to use for its border process."
            ),
            "other_official_external_authority",
            (
                "Trusted context establishes a generic foreign official "
                "operational owner, and the process is not document issuance."
            ),
            trusted_source_context={
                "publisher_family": "other_official_authority",
                "publication_family": "other_official_service",
                "authority_role": "other_official_operational_owner",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
            contrast_group="foreign_issuing_vs_general_foreign_operation",
        ),
        case(
            "iv4_034",
            (
                "What reporting procedure an overseas customs administration "
                "requires importers to use for its own customs operation."
            ),
            "other_official_external_authority",
            (
                "Trusted context identifies a generic official operational "
                "owner and no more specific frozen external class applies."
            ),
            trusted_source_context={
                "publisher_family": "other_official_authority",
                "publication_family": "other_official_service",
                "authority_role": "other_official_operational_owner",
                "certification_status": "not_applicable",
                "incorporation_status": "not_applicable",
            },
        ),

        # unresolved safety cases
        case(
            "iv4_035",
            (
                "Whether a recently announced immigration-related procedural "
                "change is already authoritative."
            ),
            "unresolved",
            (
                "The proposition does not identify whether the change is a "
                "certified instruction, non-Manual publication, or another "
                "source, and no trusted context is supplied."
            ),
            contrast_group="certified_transition_vs_unverified_change",
        ),
        case(
            "iv4_036",
            (
                "Which official organisation controls an unspecified overseas "
                "clearance process."
            ),
            "unresolved",
            (
                "The proposition does not establish whether the process is "
                "issuing, assessment, professional, entitlement, or another "
                "official role."
            ),
        ),
        case(
            "iv4_037",
            (
                "Whether an unnamed current service value found on an official "
                "website belongs to Immigration New Zealand or another agency."
            ),
            "unresolved",
            (
                "The current-value semantics do not identify the authoritative "
                "owner."
            ),
        ),
        case(
            "iv4_038",
            (
                "What procedure an official overseas authority requires, where "
                "its operational role is not stated and no trusted source "
                "metadata is available."
            ),
            "unresolved",
            (
                "Several external source classes remain plausible and the "
                "context-gated generic class cannot be established."
            ),
            contrast_group="generic_official_with_vs_without_context",
        ),
        case(
            "iv4_039",
            (
                "Whether an immigration-related fee mentioned in an undated "
                "secondary document is the current payable amount or only a "
                "historical legal reference."
            ),
            "unresolved",
            (
                "The proposition does not establish whether it concerns a "
                "current charge value or legal/historical basis."
            ),
        ),
        case(
            "iv4_040",
            (
                "Which operational rule applies when a source description could "
                "refer either to certified immigration instructions or to an "
                "uncertified staff guidance document."
            ),
            "unresolved",
            (
                "The source family is materially ambiguous and no trusted "
                "publication context resolves it."
            ),
            contrast_group="generic_official_with_vs_without_context",
        ),
    ]

    if len(tests) != 40:
        raise RuntimeError(
            f"Independent pack must contain exactly 40 tests; got {len(tests)}."
        )

    case_ids = [item["case_id"] for item in tests]

    if len(set(case_ids)) != len(case_ids):
        raise RuntimeError("Independent pack contains duplicate case IDs.")

    if any(case_id.startswith("sbv") for case_id in case_ids):
        raise RuntimeError(
            "Observed-pack case-ID family leaked into independent pack."
        )

    class_counts = Counter(
        item["expected"]["source_class"]
        for item in tests
    )

    expected_class_counts = {
        "operational_manual_instruction": 4,
        "manual_instruction_transition": 3,
        "legislation_or_regulation": 3,
        "inz_live_service_information": 4,
        "current_fee_or_charge_information": 3,
        "inz_non_manual_procedure_or_interpretation": 3,
        "foreign_issuing_authority_procedure": 3,
        "external_agency_assessment_or_service": 3,
        "external_entitlement_or_service_regime": 3,
        "professional_or_assessor_guidance": 3,
        "other_official_external_authority": 2,
        "unresolved": 6,
    }

    if dict(class_counts) != expected_class_counts:
        raise RuntimeError(
            "Independent pack source-class distribution changed."
        )

    resolved_count = sum(
        1
        for item in tests
        if item["expected"]["resolution_status"] == "resolved"
    )

    unresolved_count = sum(
        1
        for item in tests
        if item["expected"]["resolution_status"] == "unresolved"
    )

    if (resolved_count, unresolved_count) != (34, 6):
        raise RuntimeError(
            "Independent pack must contain 34 resolved and 6 unresolved cases."
        )

    groups: dict[str, list[str]] = defaultdict(list)

    for item in tests:
        group = item.get("contrast_group")
        if isinstance(group, str) and group:
            groups[group].append(item["case_id"])

    if len(groups) != 12:
        raise RuntimeError(
            f"Independent pack must contain 12 contrast groups; got {len(groups)}."
        )

    for group, members in groups.items():
        if len(members) < 2:
            raise RuntimeError(
                f"Contrast group {group!r} must contain at least two members."
            )

    pack = {
        "schema": (
            "waypoint-source-boundary-classifier-independent-contract-test-pack-v4"
        ),
        "status": (
            "FROZEN_INDEPENDENT_SYNTHETIC_PACK_READY_FOR_HUMAN_REVIEW"
        ),
        "frozen_on": str(date.today()),
        "source_artifacts": {
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "authoritative_source_boundary_v1_sha256": (
                EXPECTED_BOUNDARY_SHA256
            ),
            "classifier_design_v3_sha256": (
                EXPECTED_DESIGN_V3_SHA256
            ),
        },
        "construction": {
            "purpose": (
                "Independent synthetic acceptance pack for frozen classifier "
                "design v3."
            ),
            "test_count": 40,
            "resolved_count": 34,
            "unresolved_count": 6,
            "source_class_count": 12,
            "contrast_group_count": 12,
            "model_calls": 0,
            "reads_observed_contract_pack": False,
            "reads_observed_predictions": False,
            "reads_observed_score": False,
            "reads_failure_analysis": False,
            "uses_observed_case_ids": False,
            "copies_observed_case_wording": False,
            "benchmark_specific_logic": False,
            "question_specific_logic": False,
        },
        "coverage": {
            "source_class_counts": expected_class_counts,
            "contrast_groups": dict(groups),
            "required_design_v3_boundaries": {
                "semantic_resolution_without_context": [
                    "operational_manual_instruction",
                    "legislation_or_regulation",
                    "inz_live_service_information",
                    "current_fee_or_charge_information",
                    "foreign_issuing_authority_procedure",
                    "external_agency_assessment_or_service",
                    "external_entitlement_or_service_regime",
                    "professional_or_assessor_guidance",
                ],
                "context_gated_classes": [
                    "manual_instruction_transition",
                    "inz_non_manual_procedure_or_interpretation",
                    "other_official_external_authority",
                ],
                "unresolved_safety_cases": 6,
                "foreign_issuing_boundary_tested": True,
                "fee_vs_legal_basis_tested": True,
                "live_service_vs_instruction_tested": True,
                "professional_vs_agency_precedence_tested": True,
                "generic_other_official_context_gate_tested": True,
            },
        },
        "scoring_contract": {
            "primary_scored_field": "source_class",
            "derived_fields": [
                "resolution_status",
                "source_domain",
                "responsible_authority_type",
            ],
            "four_field_exact_match_after_derivation": True,
            "basis_scored": False,
            "prediction_error_is_incorrect": True,
            "malformed_output_is_incorrect": True,
            "contrast_group_full_consistency": (
                "A group passes only if every member is four-field correct "
                "after deterministic derivation."
            ),
            "unresolved_recall_definition": (
                "Among gold-unresolved cases, predicted source_class must be "
                "unresolved."
            ),
            "resolved_recall_definition": (
                "Among gold-resolved cases, predicted source_class must not be "
                "unresolved and the derived four-field result must be exact."
            ),
        },
        "tests": tests,
        "authorisations": {
            "human_review_authorised": True,
            "acceptance_threshold_freeze_authorised": False,
            "classifier_implementation_v2_authorised": False,
            "classifier_prompt_change_authorised": False,
            "classifier_model_run_authorised": False,
            "observed_pack_rerun_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": (
                "human_review_source_boundary_classifier_independent_pack_v4"
            ),
            "authorised": True,
            "model_calls": 0,
            "purpose": (
                "Review independence, class labels, context requirements, "
                "contrast groups, and scoring contract before any threshold "
                "or implementation work."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(
            pack,
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_INDEPENDENT_SYNTHETIC_PACK_READY_FOR_HUMAN_REVIEW"
    ):
        raise RuntimeError(
            "Saved independent pack status changed."
        )

    if saved.get(
        "construction",
        {},
    ).get("test_count") != 40:
        raise RuntimeError("Saved independent pack test count changed.")

    if saved.get(
        "coverage",
        {},
    ).get("source_class_counts") != expected_class_counts:
        raise RuntimeError(
            "Saved independent pack class distribution changed."
        )

    auth = saved.get("authorisations", {})

    if auth.get("human_review_authorised") is not True:
        raise RuntimeError(
            "Independent pack human review was not authorised."
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
                f"Independent pack unexpectedly authorises {forbidden}."
            )

    print("Waypoint independent classifier contract pack v4 freeze")
    print("=" * 63)
    print(f"Design-v3 SHA256:           {sha256(DESIGN_V3_PATH)}")
    print(f"Boundary SHA256:            {sha256(BOUNDARY_PATH)}")
    print()
    print("Independent construction")
    print("-" * 63)
    print("Tests:                      40")
    print("Resolved:                   34")
    print("Unresolved:                 6")
    print("Source classes:             12")
    print("Contrast groups:            12")
    print("Observed pack read:         NO")
    print("Observed predictions read:  NO")
    print("Observed score read:        NO")
    print("Failure analysis read:      NO")
    print("Observed case IDs used:     NO")
    print("Model calls:                NONE")
    print()
    print("Coverage")
    print("-" * 63)

    for source_class in SOURCE_CLASSES:
        print(
            f"{source_class}: "
            f"{expected_class_counts[source_class]}"
        )

    print()
    print("Pack v4:                    FROZEN")
    print("Human review:               AUTHORISED")
    print("Threshold freeze:           NOT AUTHORISED")
    print("Implementation:             NOT AUTHORISED")
    print("Prompt change:              NOT AUTHORISED")
    print("Model run:                  NOT AUTHORISED")
    print("Candidate v7:               NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next task:                  HUMAN REVIEW PACK V4")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Pack-v4 SHA256:             {sha256(OUTPUT_PATH)}")
    print()
    print("Runtime files modified:     NONE")
    print()
    print("Independent contract pack v4 freeze: PASS")


if __name__ == "__main__":
    main()
