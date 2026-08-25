"""Build and freeze the independent source-boundary classifier contract test pack.

This artifact is derived only from the frozen source-boundary classifier
design. It does not read retired external benchmark questions, gold labels,
prediction files, expected sections, or failure-case notes.

Run from backend/:
    uv run python -m py_compile scripts/build_source_boundary_classifier_contract_test_pack.py
    uv run python -m scripts.build_source_boundary_classifier_contract_test_pack

Output:
    tests/source_boundary_classifier_contract_test_pack_v1.json
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

CLASSIFIER_DESIGN_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_design_v1.json"
)

BOUNDARY_PATH = (
    BACKEND_DIR
    / "tests"
    / "authoritative_source_boundary_spec_v1.json"
)

RUNTIME_PATH = (
    BACKEND_DIR
    / "app"
    / "api"
    / "routes"
    / "ask.py"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "source_boundary_classifier_contract_test_pack_v1.json"
)

EXPECTED_CLASSIFIER_DESIGN_SHA256 = (
    "9443153C67A690EC24177BE61AA28CAB5"
    "E4794A90A171E44F3FAB4216A05F69F"
)

EXPECTED_BOUNDARY_SHA256 = (
    "2BFC518CFD892FE54AD9E46EAEE0037A9"
    "05730DDA934E3EEAEB1EBAD42C1458F"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
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
            "Refusing to build the independent contract test pack."
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
            f"Contract test pack already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        CLASSIFIER_DESIGN_PATH,
        EXPECTED_CLASSIFIER_DESIGN_SHA256,
        "Frozen source-boundary classifier design",
    )
    require_sha(
        BOUNDARY_PATH,
        EXPECTED_BOUNDARY_SHA256,
        "Frozen authoritative-source boundary",
    )
    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )

    design = load_json(CLASSIFIER_DESIGN_PATH)

    if design.get("schema") != (
        "waypoint-source-boundary-classifier-design-v1"
    ):
        raise RuntimeError("Unexpected classifier-design schema.")

    if design.get("status") != (
        "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError("Unexpected classifier-design status.")

    authorisations = design.get("authorisations", {})

    if authorisations.get(
        "independent_contract_test_pack_build_authorised"
    ) is not True:
        raise RuntimeError(
            "Classifier design does not authorise test-pack build."
        )

    if authorisations.get(
        "classifier_runtime_implementation_authorised"
    ) is not False:
        raise RuntimeError(
            "Classifier design unexpectedly authorises implementation."
        )

    tests = [
        resolved(
            test_id="sb01",
            proposition=(
                "Whether a temporary visa holder may work in self-employment "
                "under the conditions of that visa."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is a visa-condition rule and therefore "
                "belongs to certified immigration instructions."
            ),
            contrast_group="visa_rule_vs_live_service",
        ),
        resolved(
            test_id="sb02",
            proposition=(
                "Whether an applicant must provide a specified category of "
                "evidence to meet an immigration criterion."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration evidence requirement."
            ),
            contrast_group="immigration_requirement_vs_external_procedure",
        ),
        resolved(
            test_id="sb03",
            proposition=(
                "Whether a stated exception removes an applicant from an "
                "otherwise applicable immigration requirement."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration exception rule."
            ),
            contrast_group="instruction_vs_nonmanual_guidance",
        ),
        resolved(
            test_id="sb04",
            proposition=(
                "How Immigration New Zealand defines a term that determines "
                "whether an immigration criterion is met."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration definition used to apply "
                "certified instructions."
            ),
            contrast_group="legal_power_vs_instruction_content",
        ),
        resolved(
            test_id="sb05",
            proposition=(
                "Whether a newly certified immigration criterion applies from "
                "its stated effective date before the indexed Manual copy has "
                "been refreshed."
            ),
            source_domain="certified_immigration_instructions",
            source_class="manual_instruction_transition",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "Trusted metadata explicitly establishes a certified "
                "instruction transition state."
            ),
            contrast_group="transition_with_metadata_vs_recency_only",
            trusted_source_context={
                "source_family": "certified_amendment",
                "certification_status": "certified",
                "incorporation_status": "not_yet_indexed",
            },
        ),
        resolved(
            test_id="sb06",
            proposition=(
                "Whether a certified amendment changes an existing visa "
                "condition while the local indexed Manual still contains the "
                "earlier wording."
            ),
            source_domain="certified_immigration_instructions",
            source_class="manual_instruction_transition",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "Trusted metadata identifies a certified amendment awaiting "
                "local incorporation."
            ),
            trusted_source_context={
                "source_family": "certified_amendment",
                "certification_status": "certified",
                "local_index_status": "stale",
            },
        ),
        resolved(
            test_id="sb07",
            proposition=(
                "Whether the law gives the Minister power to certify "
                "immigration instructions."
            ),
            source_domain="legislation_or_regulation",
            source_class="legislation_or_regulation",
            responsible_authority_type="new_zealand_legislation",
            basis=(
                "The proposition concerns statutory authority rather than "
                "the content of an immigration instruction."
            ),
            contrast_group="legal_power_vs_instruction_content",
        ),
        resolved(
            test_id="sb08",
            proposition=(
                "Whether a procedural requirement is prescribed directly by "
                "immigration regulations rather than by certified "
                "instructions."
            ),
            source_domain="legislation_or_regulation",
            source_class="legislation_or_regulation",
            responsible_authority_type="new_zealand_legislation",
            basis=(
                "The proposition is explicitly regulatory in nature."
            ),
        ),
        resolved(
            test_id="sb09",
            proposition=(
                "The current median processing time shown for a visa service "
                "today."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_live_service_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is a current, time-varying INZ service value."
            ),
            contrast_group="visa_rule_vs_live_service",
        ),
        resolved(
            test_id="sb10",
            proposition=(
                "Whether applications are currently being accepted through a "
                "particular INZ submission channel."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_live_service_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is current operational channel availability."
            ),
        ),
        resolved(
            test_id="sb11",
            proposition=(
                "Whether places are currently available in a capped or "
                "balloted immigration service."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_live_service_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is a current operational availability state."
            ),
        ),
        resolved(
            test_id="sb12",
            proposition=(
                "The amount an applicant in a specified location would be "
                "charged today for submitting a visa application."
            ),
            source_domain="official_inz_non_manual",
            source_class="current_fee_or_charge_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition asks for the current payable amount rather "
                "than the legal authority for charging it."
            ),
            contrast_group="fee_legal_basis_vs_current_amount",
        ),
        resolved(
            test_id="sb13",
            proposition=(
                "The current immigration levy amount included in an "
                "application charge."
            ),
            source_domain="official_inz_non_manual",
            source_class="current_fee_or_charge_information",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is the current charge value."
            ),
        ),
        resolved(
            test_id="sb14",
            proposition=(
                "Which internal processing step INZ staff follow when an "
                "application is transferred between offices."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_non_manual_procedure_or_interpretation",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition concerns administrative staff procedure, "
                "not an immigration eligibility rule."
            ),
            contrast_group="instruction_vs_nonmanual_guidance",
        ),
        resolved(
            test_id="sb15",
            proposition=(
                "How an official INZ form is operationally handled after a "
                "particular supporting document is received."
            ),
            source_domain="official_inz_non_manual",
            source_class="inz_non_manual_procedure_or_interpretation",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition concerns form-specific operational handling."
            ),
        ),
        resolved(
            test_id="sb16",
            proposition=(
                "Which option a foreign police authority requires an "
                "applicant to select on that country's police-certificate "
                "request form."
            ),
            source_domain="responsible_external_official_authority",
            source_class="foreign_issuing_authority_procedure",
            responsible_authority_type="foreign_issuing_authority",
            basis=(
                "The proposition concerns the foreign authority's own issuing "
                "procedure."
            ),
            contrast_group="immigration_requirement_vs_external_procedure",
        ),
        resolved(
            test_id="sb17",
            proposition=(
                "How a foreign government office requires fingerprints or "
                "identity documents to be submitted when requesting an "
                "official clearance."
            ),
            source_domain="responsible_external_official_authority",
            source_class="foreign_issuing_authority_procedure",
            responsible_authority_type="foreign_issuing_authority",
            basis=(
                "The proposition is owned by the foreign document-issuing "
                "authority."
            ),
        ),
        resolved(
            test_id="sb18",
            proposition=(
                "Which qualification-assessment service type another New "
                "Zealand agency requires for a particular recognition task."
            ),
            source_domain="responsible_external_official_authority",
            source_class="external_agency_assessment_or_service",
            responsible_authority_type="new_zealand_external_agency",
            basis=(
                "The proposition concerns another agency's assessment service."
            ),
            contrast_group="immigration_qualification_rule_vs_agency_service",
        ),
        resolved(
            test_id="sb19",
            proposition=(
                "How a New Zealand statutory body assesses an overseas "
                "qualification submitted to its recognition service."
            ),
            source_domain="responsible_external_official_authority",
            source_class="external_agency_assessment_or_service",
            responsible_authority_type="new_zealand_external_agency",
            basis=(
                "The proposition is the external agency's assessment process."
            ),
        ),
        resolved(
            test_id="sb20",
            proposition=(
                "Whether a person qualifies for publicly funded health "
                "services under the health-system eligibility rules."
            ),
            source_domain="responsible_external_official_authority",
            source_class="external_entitlement_or_service_regime",
            responsible_authority_type="public_service_authority",
            basis=(
                "The proposition concerns a separate public-service "
                "entitlement regime."
            ),
            contrast_group="immigration_health_rule_vs_public_entitlement",
        ),
        resolved(
            test_id="sb21",
            proposition=(
                "Whether a person is entitled to a separately administered "
                "public service because of their current status."
            ),
            source_domain="responsible_external_official_authority",
            source_class="external_entitlement_or_service_regime",
            responsible_authority_type="public_service_authority",
            basis=(
                "The proposition is owned by the responsible public-service "
                "authority, not by immigration instructions."
            ),
        ),
        resolved(
            test_id="sb22",
            proposition=(
                "Whether a clinical assessor requires a particular specialist "
                "report before completing an assessment."
            ),
            source_domain="responsible_external_official_authority",
            source_class="professional_or_assessor_guidance",
            responsible_authority_type="professional_or_assessment_authority",
            basis=(
                "The proposition concerns assessor or professional procedure."
            ),
            contrast_group="immigration_health_rule_vs_professional_guidance",
        ),
        resolved(
            test_id="sb23",
            proposition=(
                "Which documents a professional registration authority "
                "requires before it will assess an applicant's registration."
            ),
            source_domain="responsible_external_official_authority",
            source_class="professional_or_assessor_guidance",
            responsible_authority_type="professional_or_assessment_authority",
            basis=(
                "The proposition is a professional registration procedure."
            ),
        ),
        resolved(
            test_id="sb24",
            proposition=(
                "Whether an official overseas licensing authority requires a "
                "separate verification step before recognising a credential."
            ),
            source_domain="responsible_external_official_authority",
            source_class="other_official_external_authority",
            responsible_authority_type="other_official_authority",
            basis=(
                "The proposition clearly belongs to an identifiable official "
                "authority outside the frozen more-specific classes."
            ),
        ),
        resolved(
            test_id="sb25",
            proposition=(
                "Whether an official non-immigration regulator requires a "
                "specific authorisation before a regulated activity may be "
                "performed."
            ),
            source_domain="responsible_external_official_authority",
            source_class="other_official_external_authority",
            responsible_authority_type="other_official_authority",
            basis=(
                "The proposition is owned by another identifiable official "
                "regulator but does not fit a more specific frozen class."
            ),
        ),
        resolved(
            test_id="sb29",
            proposition=(
                "Whether immigration regulations prescribe the legal basis "
                "for charging an application fee or levy."
            ),
            source_domain="legislation_or_regulation",
            source_class="legislation_or_regulation",
            responsible_authority_type="new_zealand_legislation",
            basis=(
                "The proposition concerns the legal basis for a prescribed "
                "charge, not the current amount payable."
            ),
            contrast_group="fee_legal_basis_vs_current_amount",
        ),
        resolved(
            test_id="sb30",
            proposition=(
                "Whether an immigration criterion accepts a specified type "
                "of qualification evidence when assessing visa eligibility."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration eligibility and evidence "
                "rule, not another agency's qualification-assessment service."
            ),
            contrast_group="immigration_qualification_rule_vs_agency_service",
        ),
        resolved(
            test_id="sb31",
            proposition=(
                "Whether an applicant must satisfy a stated immigration "
                "health criterion before a visa may be granted."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration health eligibility rule, "
                "not eligibility for a separately administered public "
                "health service."
            ),
            contrast_group="immigration_health_rule_vs_public_entitlement",
        ),
        resolved(
            test_id="sb32",
            proposition=(
                "Whether certified immigration instructions require medical "
                "evidence for a particular visa assessment."
            ),
            source_domain="certified_immigration_instructions",
            source_class="operational_manual_instruction",
            responsible_authority_type="immigration_new_zealand",
            basis=(
                "The proposition is an immigration evidence requirement, "
                "not a clinician's or assessor's procedural guidance."
            ),
            contrast_group="immigration_health_rule_vs_professional_guidance",
        ),
        unresolved(
            test_id="sb26",
            proposition=(
                "Whether a recently announced change will apply to a future "
                "application, where no trusted source metadata identifies "
                "whether the change is certified instructions, legislation, "
                "or non-binding guidance."
            ),
            basis=(
                "Recency and future-effective wording alone are insufficient "
                "to identify authoritative ownership."
            ),
            contrast_group="transition_with_metadata_vs_recency_only",
        ),
        unresolved(
            test_id="sb27",
            proposition=(
                "Whether an unspecified government authority requires an "
                "additional document, where the proposition does not identify "
                "which authority owns the requirement."
            ),
            basis=(
                "The responsible authority cannot be resolved from the "
                "proposition."
            ),
        ),
        unresolved(
            test_id="sb28",
            proposition=(
                "Whether a published rule described only as official guidance "
                "is legally binding, where no source family or authority is "
                "identified."
            ),
            basis=(
                "The wording is insufficient to distinguish certified "
                "instructions, legislation, or non-Manual guidance."
            ),
        ),
    ]

    if len(tests) != 32:
        raise RuntimeError(
            f"Expected 32 synthetic contract tests, got {len(tests)}."
        )

    ids = [item["test_id"] for item in tests]
    if len(ids) != len(set(ids)):
        raise RuntimeError("Duplicate synthetic test_id values.")

    expected_classes = {
        item["expected"]["source_class"]
        for item in tests
    }

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

    if expected_classes != required_classes:
        raise RuntimeError(
            "Synthetic test pack does not cover every frozen source class."
        )

    resolved_count = sum(
        item["expected"]["resolution_status"] == "resolved"
        for item in tests
    )
    unresolved_count = sum(
        item["expected"]["resolution_status"] == "unresolved"
        for item in tests
    )

    if (resolved_count, unresolved_count) != (29, 3):
        raise RuntimeError(
            "Unexpected resolved/unresolved synthetic test distribution."
        )

    transition_cases = [
        item
        for item in tests
        if item["expected"]["source_class"]
        == "manual_instruction_transition"
    ]

    if len(transition_cases) != 2:
        raise RuntimeError("Expected 2 transition cases.")

    if any(
        not isinstance(item.get("trusted_source_context"), dict)
        for item in transition_cases
    ):
        raise RuntimeError(
            "Every transition case must contain trusted source context."
        )

    contrast_groups = {}
    for item in tests:
        group = item.get("contrast_group")
        if group:
            contrast_groups.setdefault(group, []).append(item["test_id"])

    if len(contrast_groups) != 9:
        raise RuntimeError(
            f"Expected exactly 9 independent contrast groups, "
            f"got {len(contrast_groups)}."
        )

    singleton_groups = {
        group: ids
        for group, ids in contrast_groups.items()
        if len(ids) < 2
    }

    if singleton_groups:
        raise RuntimeError(
            "Every contrast group must contain at least two tests. "
            f"Singleton groups: {singleton_groups}"
        )

    class_counts = {}
    for item in tests:
        source_class = item["expected"]["source_class"]
        class_counts[source_class] = class_counts.get(source_class, 0) + 1

    for source_class in required_classes - {"unresolved"}:
        if class_counts.get(source_class, 0) < 2:
            raise RuntimeError(
                f"Resolved source class has fewer than two tests: "
                f"{source_class}"
            )

    if class_counts.get("unresolved") != 3:
        raise RuntimeError("Expected exactly 3 unresolved tests.")

    pack = {
        "schema": (
            "waypoint-source-boundary-classifier-contract-test-pack-v1"
        ),
        "status": "FROZEN_SYNTHETIC_CONTRACT_TEST_PACK_NO_RUNTIME_CHANGE",
        "frozen_on": str(date.today()),
        "construction": {
            "basis": (
                "Synthetic unsupported propositions derived only from the "
                "frozen source-boundary classifier contract."
            ),
            "retired_external_benchmark_questions_read": False,
            "gold_files_read": False,
            "prediction_files_read": False,
            "failure_taxonomy_read": False,
            "expected_sections_read": False,
            "model_generated": False,
            "test_count": len(tests),
            "resolved_count": resolved_count,
            "unresolved_count": unresolved_count,
        },
        "source_artifacts": {
            "classifier_design_sha256": (
                EXPECTED_CLASSIFIER_DESIGN_SHA256
            ),
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "production_runtime_sha256": EXPECTED_RUNTIME_SHA256,
        },
        "coverage": {
            "source_class_counts": class_counts,
            "contrast_groups": contrast_groups,
        },
        "scoring_contract": {
            "primary": (
                "Exact match on resolution_status, source_domain, "
                "source_class, and responsible_authority_type."
            ),
            "basis_text": (
                "Diagnostic only. Free-text basis is not used for exact-match "
                "scoring."
            ),
            "malformed_output": "incorrect",
            "classifier_error": "incorrect",
            "unresolved_expected_case": (
                "Correct only if every frozen unresolved output field is "
                "returned as unresolved."
            ),
            "automatic_retry": False,
        },
        "tests": tests,
        "authorisations": {
            "classifier_contract_test_pack_frozen": True,
            "classifier_experimental_implementation_design_authorised": False,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_step": {
            "name": "human_review_contract_test_pack",
            "authorised": True,
            "purpose": (
                "Review the synthetic propositions and expected source "
                "ownership for independence, coverage, and ambiguity before "
                "any classifier implementation design is authorised."
            ),
        },
    }

    serialised = json.dumps(
        pack,
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
            rf'"{re.escape(key)}"\\s*:',
            serialised,
            flags=re.IGNORECASE,
        ):
            raise RuntimeError(
                f"Forbidden benchmark/evaluation field in pack: {key}"
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
            "Forbidden retired benchmark IDs in test pack: "
            f"{benchmark_ids}"
        )

    section_literals = sorted(
        set(
            re.findall(
                r'"([A-Z]{1,3}\d+(?:\.\d+)*)"',
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

    verify = load_json(OUTPUT_PATH)

    if verify.get("construction", {}).get(
        "retired_external_benchmark_questions_read"
    ) is not False:
        raise RuntimeError(
            "Saved pack independence metadata changed."
        )

    if verify.get("authorisations", {}).get(
        "candidate_v7_build_authorised"
    ) is not False:
        raise RuntimeError(
            "Test pack unexpectedly authorises candidate v7."
        )

    if verify.get("next_step", {}).get(
        "name"
    ) != "human_review_contract_test_pack":
        raise RuntimeError(
            "Unexpected test-pack next step."
        )

    print("Waypoint source-boundary classifier contract test-pack freeze")
    print("=" * 61)
    print(f"Production v2 SHA256:       {sha256(RUNTIME_PATH)}")
    print(
        f"Classifier design SHA256:   "
        f"{sha256(CLASSIFIER_DESIGN_PATH)}"
    )
    print(f"Boundary spec SHA256:       {sha256(BOUNDARY_PATH)}")
    print()
    print("Construction basis:         SYNTHETIC SOURCE ARCHITECTURE")
    print("Retired benchmark read:     NO")
    print("Gold files read:            NO")
    print("Prediction files read:      NO")
    print("Failure taxonomy read:      NO")
    print("Expected sections read:     NO")
    print()
    print(f"Synthetic tests:            {len(tests)}")
    print(f"Resolved expected:          {resolved_count}")
    print(f"Unresolved expected:        {unresolved_count}")
    print(f"Source classes covered:     {len(class_counts)}")
    print(f"Contrast groups:            {len(contrast_groups)}")
    print()
    print("Scoring")
    print("-" * 61)
    print("resolution_status:          EXACT MATCH")
    print("source_domain:              EXACT MATCH")
    print("source_class:               EXACT MATCH")
    print("responsible_authority_type: EXACT MATCH")
    print("Malformed/error:            INCORRECT")
    print("Automatic retry:            NO")
    print()
    print("Classifier implementation:  NOT AUTHORISED")
    print("Candidate v7 build:         NOT AUTHORISED")
    print("Production change:          NOT AUTHORISED")
    print("Fresh external-v3:          NOT AUTHORISED")
    print()
    print("Next step:                  HUMAN REVIEW OF TEST PACK")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Test-pack SHA256:           {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Source-boundary contract test-pack freeze: PASS")


if __name__ == "__main__":
    main()
