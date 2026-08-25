"""Freeze the source-boundary classifier design for Waypoint.

DESIGN ONLY. No runtime implementation is authorised.

Run from backend/:
    uv run python -m py_compile scripts/freeze_source_boundary_classifier_design.py
    uv run python -m scripts.freeze_source_boundary_classifier_design

Output:
    tests/source_boundary_classifier_design_v1.json
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

BOUNDARY_PATH = (
    BACKEND_DIR
    / "tests"
    / "authoritative_source_boundary_spec_v1.json"
)

DIAGNOSIS_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_architecture_diagnosis_v1.json"
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
    / "source_boundary_classifier_design_v1.json"
)

EXPECTED_BOUNDARY_SHA256 = (
    "2BFC518CFD892FE54AD9E46EAEE0037A9"
    "05730DDA934E3EEAEB1EBAD42C1458F"
)

EXPECTED_DIAGNOSIS_SHA256 = (
    "7DCC8FA8E2B80C3146E63B8D64839411"
    "F353026671B11FBEC1F1C672DF943029"
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
            "Refusing to freeze the classifier design."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Classifier design already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        BOUNDARY_PATH,
        EXPECTED_BOUNDARY_SHA256,
        "Frozen authoritative-source boundary",
    )
    require_sha(
        DIAGNOSIS_PATH,
        EXPECTED_DIAGNOSIS_SHA256,
        "Frozen answer-architecture diagnosis",
    )
    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )

    boundary = load_json(BOUNDARY_PATH)
    diagnosis = load_json(DIAGNOSIS_PATH)

    if boundary.get("schema") != (
        "waypoint-authoritative-source-boundary-spec-v1"
    ):
        raise RuntimeError("Unexpected source-boundary schema.")

    if boundary.get("status") != (
        "FROZEN_SOURCE_ARCHITECTURE_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError("Unexpected source-boundary status.")

    if boundary.get("next_engineering_task", {}).get(
        "name"
    ) != "source_boundary_classifier_design":
        raise RuntimeError(
            "Frozen source boundary does not authorise this design task."
        )

    if boundary.get("next_engineering_task", {}).get(
        "runtime_implementation_authorised"
    ) is not False:
        raise RuntimeError(
            "Source boundary unexpectedly authorises implementation."
        )

    if diagnosis.get("decisions", {}).get(
        "candidate_v7_build_authorised"
    ) is not False:
        raise RuntimeError(
            "Diagnosis unexpectedly authorises candidate v7."
        )

    design = {
        "schema": "waypoint-source-boundary-classifier-design-v1",
        "status": "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE",
        "frozen_on": str(date.today()),
        "purpose": (
            "Classify the authoritative source domain of one exact material "
            "proposition that has already been determined to be unsupported "
            "by the supplied Operational Manual evidence."
        ),
        "baseline": {
            "production_candidate": "evidence_adequacy_v2",
            "runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "source_boundary_sha256": EXPECTED_BOUNDARY_SHA256,
            "diagnosis_sha256": EXPECTED_DIAGNOSIS_SHA256,
        },
        "preconditions": [
            (
                "A separate upstream process has already determined that the "
                "retrieved Operational Manual evidence is insufficient for "
                "one material proposition."
            ),
            (
                "The unsupported proposition is stated neutrally and does "
                "not contain a guessed answer."
            ),
            (
                "The classifier is not asked whether the user's overall "
                "question is answerable."
            ),
        ],
        "classifier_input": {
            "unsupported_proposition": {
                "type": "string",
                "required": True,
                "description": (
                    "The exact material proposition whose authoritative "
                    "owner must be resolved."
                ),
            },
            "trusted_source_context": {
                "type": "object | null",
                "required": False,
                "description": (
                    "Optional trusted metadata about a source transition or "
                    "official source identity. It must never contain gold "
                    "labels, expected sections, benchmark IDs, or model "
                    "answers."
                ),
                "allowed_uses": [
                    (
                        "Confirm that a proposition is from a certified "
                        "immigration-instruction amendment that has not yet "
                        "been incorporated/indexed."
                    ),
                    (
                        "Confirm an explicitly identified official source "
                        "family when supplied by a separate trusted source "
                        "registry."
                    ),
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
                "A concise explanation of why this proposition type belongs "
                "to the selected authoritative source class. It must not "
                "answer the proposition."
            ),
        },
        "source_class_contracts": [
            {
                "source_class": "operational_manual_instruction",
                "source_domain": "certified_immigration_instructions",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "The proposition is itself an immigration rule, visa "
                    "criterion, visa condition, evidence requirement, "
                    "immigration exception, immigration definition, "
                    "immigration consequence, assessment rule, verification "
                    "rule, or immigration decision criterion."
                ),
                "future_status_mapping_if_unsupported": "corpus_gap",
            },
            {
                "source_class": "manual_instruction_transition",
                "source_domain": "certified_immigration_instructions",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "Trusted source metadata establishes that the proposition "
                    "belongs to a certified immigration-instruction amendment "
                    "that is pending incorporation or indexing."
                ),
                "prohibited_inference": (
                    "Do not infer this class from recency wording, future "
                    "dates, or absence from retrieved Manual passages alone."
                ),
                "future_status_mapping_if_unsupported": "corpus_gap",
            },
            {
                "source_class": "legislation_or_regulation",
                "source_domain": "legislation_or_regulation",
                "responsible_authority_type": "new_zealand_legislation",
                "use_when": (
                    "The proposition concerns statutory power, a legal rule, "
                    "a prescribed regulatory requirement, a visa waiver fixed "
                    "by regulation, or another legal requirement whose "
                    "authority is legislation or regulations rather than "
                    "certified immigration instructions."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "inz_live_service_information",
                "source_domain": "official_inz_non_manual",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "The proposition asks for a current or time-varying INZ "
                    "service value or operational state, such as a current "
                    "processing timeframe, current application status, "
                    "current place or ballot availability, current receiving "
                    "location, or current channel availability."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "current_fee_or_charge_information",
                "source_domain": "official_inz_non_manual",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "The proposition asks for the current amount payable, "
                    "including a fee, levy, location-dependent charge, "
                    "citizenship-dependent charge, or current fee-waiver "
                    "result."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
            },
            {
                "source_class": (
                    "inz_non_manual_procedure_or_interpretation"
                ),
                "source_domain": "official_inz_non_manual",
                "responsible_authority_type": "immigration_new_zealand",
                "use_when": (
                    "The proposition concerns an official INZ administrative "
                    "procedure, staff handling process, form-specific "
                    "procedure, or published interpretation that is "
                    "maintained outside certified immigration instructions."
                ),
                "precedence_guardrail": (
                    "This class may clarify administration or interpretation "
                    "but cannot override legislation or certified "
                    "immigration instructions."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "foreign_issuing_authority_procedure",
                "source_domain": (
                    "responsible_external_official_authority"
                ),
                "responsible_authority_type": (
                    "foreign_issuing_authority"
                ),
                "use_when": (
                    "The proposition concerns how a foreign authority issues "
                    "or requires an application for a foreign official "
                    "document, including the foreign procedure or form option."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
            },
            {
                "source_class": (
                    "external_agency_assessment_or_service"
                ),
                "source_domain": (
                    "responsible_external_official_authority"
                ),
                "responsible_authority_type": (
                    "new_zealand_external_agency"
                ),
                "use_when": (
                    "The proposition concerns another New Zealand agency's "
                    "assessment, recognition service, registration process, "
                    "or service type rather than an immigration instruction."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
            },
            {
                "source_class": (
                    "external_entitlement_or_service_regime"
                ),
                "source_domain": (
                    "responsible_external_official_authority"
                ),
                "responsible_authority_type": (
                    "public_service_authority"
                ),
                "use_when": (
                    "The proposition concerns eligibility for or entitlement "
                    "to a public service, benefit, or separately administered "
                    "public regime."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "professional_or_assessor_guidance",
                "source_domain": (
                    "responsible_external_official_authority"
                ),
                "responsible_authority_type": (
                    "professional_or_assessment_authority"
                ),
                "use_when": (
                    "The proposition concerns clinical, assessor, "
                    "professional, registration, or provider-specific "
                    "guidance owned by the responsible professional or "
                    "assessment authority."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
            },
            {
                "source_class": "other_official_external_authority",
                "source_domain": (
                    "responsible_external_official_authority"
                ),
                "responsible_authority_type": "other_official_authority",
                "use_when": (
                    "The proposition is clearly owned by an identifiable "
                    "official authority outside the Operational Manual, but "
                    "does not fit a more specific frozen source class."
                ),
                "future_status_mapping_if_unsupported": (
                    "external_source_required"
                ),
                "guardrail": (
                    "This is not a catch-all for uncertainty. Use unresolved "
                    "when authoritative ownership itself is unclear."
                ),
            },
        ],
        "resolution_rules": [
            (
                "Classify the exact unsupported proposition, not the broad "
                "visa, occupation, nationality, or application topic."
            ),
            (
                "Do not use absence from retrieved Manual passages as "
                "evidence that the authority is external."
            ),
            (
                "Do not use the fact that a proposition concerns immigration "
                "as evidence that it belongs to the Operational Manual."
            ),
            (
                "First determine whether the proposition is itself a "
                "certified immigration rule. If yes, use the certified "
                "immigration-instruction domain unless trusted metadata "
                "establishes a transition state."
            ),
            (
                "Use legislation_or_regulation only when the proposition is "
                "legal or regulatory in nature, not merely because an "
                "immigration instruction ultimately derives authority from "
                "legislation."
            ),
            (
                "Use live-service and current-fee classes because the "
                "requested proposition is a current operational value, not "
                "because the question contains particular keywords."
            ),
            (
                "Use an external official-authority class only when the "
                "responsible authority owns the proposition itself."
            ),
            (
                "If authoritative ownership cannot be resolved from the "
                "proposition and trusted source context, return unresolved. "
                "Do not guess."
            ),
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
                "operational_manual_instruction and "
                "manual_instruction_transition require source_domain="
                "certified_immigration_instructions."
            ),
            (
                "legislation_or_regulation requires source_domain="
                "legislation_or_regulation."
            ),
            (
                "inz_live_service_information, "
                "current_fee_or_charge_information, and "
                "inz_non_manual_procedure_or_interpretation require "
                "source_domain=official_inz_non_manual."
            ),
            (
                "External agency, entitlement, issuing-authority, "
                "professional, and other-official classes require "
                "source_domain=responsible_external_official_authority."
            ),
            (
                "manual_instruction_transition requires trusted source "
                "context. It cannot be selected from proposition text alone."
            ),
        ],
        "classifier_must_not": [
            "Answer the unsupported proposition.",
            "Generate immigration advice.",
            "Determine whether retrieved evidence is sufficient.",
            "Determine decision_boundary.",
            "Choose public evidence_status directly.",
            "Read evaluation or gold files.",
            "Use expected sections.",
            "Use benchmark case IDs.",
            "Use question-specific routing.",
            "Use visa-category-to-source mappings.",
            "Use section-code-specific routing.",
            "Use nationality-specific routing.",
            "Use occupation-specific routing.",
            "Use unrestricted web search.",
            "Silently default unresolved authority to corpus_gap.",
            (
                "Silently default unresolved authority to "
                "external_source_required."
            ),
        ],
        "future_deterministic_mapping": {
            "note": (
                "This mapping is frozen for design review only and is not "
                "implemented by this artifact."
            ),
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
                        "explicit classifier failure / unresolved authority; "
                        "do not fabricate public evidence_status"
                    ),
                },
            ],
        },
        "failure_handling": {
            "malformed_output": (
                "Fail explicitly. Do not substitute a source class."
            ),
            "unresolved_authority": (
                "Return unresolved explicitly. Do not guess."
            ),
            "inconsistent_output": (
                "Fail explicit validation. Do not coerce fields into "
                "consistency."
            ),
            "retry_policy_for_evaluation": (
                "No automatic retry when measuring classifier behaviour."
            ),
        },
        "independent_review_plan": {
            "next_required_artifact": (
                "source_boundary_classifier_contract_test_pack_v1.json"
            ),
            "purpose": (
                "Review the frozen classifier contract using synthetic "
                "propositions derived from the frozen source architecture, "
                "not from retired external benchmark questions."
            ),
            "test_pack_requirements": [
                (
                    "At least two propositions per resolved source class "
                    "where meaningful."
                ),
                (
                    "Include ambiguous propositions that should resolve to "
                    "unresolved."
                ),
                (
                    "Include contrast pairs that distinguish immigration "
                    "rules from current service values and external agency "
                    "procedures."
                ),
                (
                    "Do not copy or paraphrase retired external evaluation "
                    "questions."
                ),
                (
                    "Do not include benchmark case IDs, expected sections, "
                    "or gold evidence_status values."
                ),
            ],
        },
        "authorisations": {
            "classifier_design_frozen": True,
            "independent_contract_test_pack_build_authorised": True,
            "classifier_runtime_implementation_authorised": False,
            "candidate_v7_build_authorised": False,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
    }

    serialised = (
        json.dumps(design, indent=2, ensure_ascii=False) + "\n"
    )

    forbidden_tokens = (
        "expected_sections",
        "candidate_id",
        "case_id",
        "adjudication_note",
        "benchmark_status",
    )

    for token in forbidden_tokens:
        if token.casefold() in serialised.casefold():
            raise RuntimeError(
                f"Forbidden benchmark/evaluation token in design: {token}"
            )

    benchmark_case_ids = sorted(
        set(
            re.findall(
                r"\\bext2?_[0-9a-f]{16}\\b",
                serialised,
                flags=re.IGNORECASE,
            )
        )
    )

    if benchmark_case_ids:
        raise RuntimeError(
            "Forbidden benchmark case IDs found in design: "
            f"{benchmark_case_ids}"
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

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError(
            "Saved classifier-design status verification failed."
        )

    authorisations = saved.get("authorisations", {})

    if authorisations.get(
        "independent_contract_test_pack_build_authorised"
    ) is not True:
        raise RuntimeError(
            "Classifier design does not authorise independent test-pack build."
        )

    if authorisations.get(
        "classifier_runtime_implementation_authorised"
    ) is not False:
        raise RuntimeError(
            "Classifier design unexpectedly authorises implementation."
        )

    if authorisations.get(
        "candidate_v7_build_authorised"
    ) is not False:
        raise RuntimeError(
            "Classifier design unexpectedly authorises candidate v7."
        )

    print("Waypoint source-boundary classifier design freeze")
    print("=" * 50)
    print(f"Production v2 SHA256:      {sha256(RUNTIME_PATH)}")
    print(f"Boundary spec SHA256:      {sha256(BOUNDARY_PATH)}")
    print(f"Diagnosis SHA256:          {sha256(DIAGNOSIS_PATH)}")
    print()
    print("Classifier input:          ONE UNSUPPORTED PROPOSITION")
    print("Support decision:          OUT OF SCOPE")
    print("Answer generation:         OUT OF SCOPE")
    print("Public evidence_status:    NOT CHOSEN BY CLASSIFIER")
    print()
    print("Resolution outcomes")
    print("-" * 50)
    print("resolved")
    print("unresolved")
    print()
    print("Source domains")
    print("-" * 50)
    print("certified_immigration_instructions")
    print("legislation_or_regulation")
    print("official_inz_non_manual")
    print("responsible_external_official_authority")
    print("unresolved")
    print()
    print("Forced authority guess:    PROHIBITED")
    print("Benchmark/eval routing:    PROHIBITED")
    print("Section-specific routing:  PROHIBITED")
    print("Visa-specific source map:  PROHIBITED")
    print("Unrestricted web search:   PROHIBITED")
    print()
    print("Classifier implementation: NOT AUTHORISED")
    print("Candidate v7 build:        NOT AUTHORISED")
    print("Production change:         NOT AUTHORISED")
    print("Fresh external-v3:         NOT AUTHORISED")
    print()
    print("Next task:                 INDEPENDENT CONTRACT TEST PACK")
    print("Test-pack build:           AUTHORISED")
    print()
    print(f"Output:                    {OUTPUT_PATH}")
    print(f"Classifier design SHA256:  {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:               NONE")
    print("Retrieval/reranker calls:  NONE")
    print("Database writes:           NONE")
    print("Runtime files modified:    NONE")
    print()
    print("Source-boundary classifier design freeze: PASS")


if __name__ == "__main__":
    main()
