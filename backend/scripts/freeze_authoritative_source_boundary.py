"""Freeze Waypoint's independent authoritative-source boundary specification.

This is a SOURCE-ARCHITECTURE specification only.

It is intentionally independent of benchmark case IDs, expected sections,
gold labels, or evaluation-question mappings.

It does not:
- modify app/ runtime;
- authorise candidate v7;
- add web search;
- add external-source retrieval;
- call a model;
- call retrieval or reranking;
- write to the database.

Run from backend/:
    uv run python -m py_compile scripts/freeze_authoritative_source_boundary.py
    uv run python -m scripts.freeze_authoritative_source_boundary

Output:
    tests/authoritative_source_boundary_spec_v1.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

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
    / "authoritative_source_boundary_spec_v1.json"
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
            "Refusing to freeze the source-boundary specification."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Source-boundary specification already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
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

    diagnosis = load_json(DIAGNOSIS_PATH)

    if diagnosis.get("schema") != (
        "waypoint-answer-architecture-diagnosis-v1"
    ):
        raise RuntimeError("Unexpected diagnosis schema.")

    if diagnosis.get("status") != (
        "FROZEN_DEVELOPMENT_DIAGNOSIS_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError("Unexpected diagnosis status.")

    if diagnosis.get("next_engineering_task", {}).get(
        "name"
    ) != "independent_authoritative_source_boundary_specification":
        raise RuntimeError(
            "Frozen diagnosis does not authorise this specification task."
        )

    if diagnosis.get("next_engineering_task", {}).get(
        "runtime_implementation_authorised"
    ) is not False:
        raise RuntimeError(
            "Diagnosis unexpectedly authorises runtime implementation."
        )

    specification = {
        "schema": "waypoint-authoritative-source-boundary-spec-v1",
        "status": "FROZEN_SOURCE_ARCHITECTURE_ONLY_NO_RUNTIME_CHANGE",
        "frozen_on": str(date.today()),
        "scope": {
            "product": "Waypoint",
            "current_product_boundary": (
                "Operational Manual indexed corpus only"
            ),
            "purpose": (
                "Define generic authoritative-source ownership by proposition "
                "type before any further answer-layer candidate is designed."
            ),
            "independent_of_benchmarks": True,
        },
        "baseline": {
            "production_candidate": "evidence_adequacy_v2",
            "runtime_sha256": EXPECTED_RUNTIME_SHA256,
            "diagnosis_sha256": EXPECTED_DIAGNOSIS_SHA256,
        },
        "official_research_basis": [
            {
                "source_id": "nz_legislation_immigration_act_2009_s22",
                "publisher": "New Zealand Legislation",
                "title": "Immigration Act 2009, section 22",
                "url": (
                    "https://www.legislation.govt.nz/act/public/2009/51/"
                    "en/2026-07-10/sections/DLM1440613/"
                ),
                "supports": [
                    (
                        "The Minister may certify immigration instructions "
                        "covering visa classes, entry permission, visa "
                        "conditions, temporary-visa periods, and visa types."
                    ),
                    (
                        "Certified immigration instructions take effect from "
                        "certification or a specified later effective date."
                    ),
                ],
            },
            {
                "source_id": "nz_legislation_visa_entry_regulations_2010",
                "publisher": "New Zealand Legislation",
                "title": (
                    "Immigration (Visa, Entry Permission, and Related Matters) "
                    "Regulations 2010"
                ),
                "url": (
                    "https://www.legislation.govt.nz/regulation/public/"
                    "2010/0241/latest/versions.aspx"
                ),
                "supports": [
                    (
                        "Regulations govern legal matters including application "
                        "requirements, visa waivers, prescribed fees, "
                        "immigration levies, and related matters."
                    ),
                ],
            },
            {
                "source_id": "inz_immigration_instructions",
                "publisher": "Immigration New Zealand",
                "title": "Immigration instructions",
                "url": (
                    "https://www.immigration.govt.nz/about-us/"
                    "immigration-policy-and-law/"
                    "immigration-instructions-and-changes/"
                    "immigration-instructions/"
                ),
                "supports": [
                    (
                        "Immigration instructions are the rules, criteria, and "
                        "requirements set out in the Operational Manual."
                    ),
                    (
                        "The instructions include criteria, required evidence, "
                        "and processes used to assess and verify visa "
                        "applications."
                    ),
                ],
            },
            {
                "source_id": "inz_policy_amendment_circulars",
                "publisher": "Immigration New Zealand",
                "title": "Policy Amendment Circulars",
                "url": (
                    "https://www.immigration.govt.nz/about-us/"
                    "immigration-policy-and-law/"
                    "immigration-instructions-and-changes/"
                    "policy-amendment-circulars/"
                ),
                "supports": [
                    (
                        "Certified amendments are first published as "
                        "Amendment Circulars and incorporated into the "
                        "Operational Manual."
                    ),
                ],
            },
            {
                "source_id": "inz_internal_administration_circulars",
                "publisher": "Immigration New Zealand",
                "title": "Internal Administration Circulars",
                "url": (
                    "https://www.immigration.govt.nz/about-us/"
                    "immigration-policy-and-law/"
                    "internal-administration-circulars/"
                ),
                "supports": [
                    (
                        "IACs provide immigration staff with procedures and "
                        "process information."
                    ),
                    (
                        "IACs are not part of the Operational Manual."
                    ),
                ],
            },
            {
                "source_id": "inz_advice_to_staff",
                "publisher": "Immigration New Zealand",
                "title": "Advice to immigration staff",
                "url": (
                    "https://www.immigration.govt.nz/about-us/"
                    "immigration-policy-and-law/"
                    "advice-to-immigration-staff/"
                ),
                "supports": [
                    (
                        "Advice to staff helps immigration staff interpret and "
                        "apply immigration instructions consistently."
                    ),
                    (
                        "This advice is maintained separately from the "
                        "Operational Manual."
                    ),
                ],
            },
            {
                "source_id": "inz_processing_times",
                "publisher": "Immigration New Zealand",
                "title": "Check visa application processing times",
                "url": (
                    "https://www.immigration.govt.nz/process-to-apply/"
                    "waiting-for-a-visa/processing-a-visa-application/"
                    "how-long-it-takes-to-process-an-application/"
                    "check-visa-application-processing-time/"
                ),
                "supports": [
                    (
                        "Current visa-processing timeframes are supplied "
                        "through a separate live processing-time tool."
                    ),
                    (
                        "Published timeframes are guides based on current "
                        "application processing and may change."
                    ),
                ],
            },
            {
                "source_id": "inz_fees",
                "publisher": "Immigration New Zealand",
                "title": "How much visa applications cost and when to pay",
                "url": (
                    "https://www.immigration.govt.nz/process-to-apply/"
                    "applying-for-a-visa/fees-processing-times-and-refunds/"
                    "how-much-visa-applications-cost-and-when-to-pay/"
                ),
                "supports": [
                    (
                        "Current application cost can depend on citizenship "
                        "and current location."
                    ),
                    (
                        "INZ directs users to its Fees, decision times and "
                        "where to apply tool and Fees Guide for current costs."
                    ),
                ],
            },
            {
                "source_id": "inz_police_certificate_how_to",
                "publisher": "Immigration New Zealand",
                "title": "How to get a police certificate",
                "url": (
                    "https://www.immigration.govt.nz/process-to-apply/"
                    "applying-for-a-visa/"
                    "providing-evidence-and-documents-to-support-your-"
                    "visa-application/"
                    "good-character-requirements-and-police-certificates/"
                    "get-a-police-certificate/"
                ),
                "supports": [
                    (
                        "Country-specific police-certificate obtaining "
                        "instructions are maintained through a separate INZ "
                        "country/territory tool."
                    ),
                ],
            },
            {
                "source_id": "nzqa_iqa",
                "publisher": "New Zealand Qualifications Authority",
                "title": (
                    "Find out if you need an International Qualification "
                    "Assessment"
                ),
                "url": (
                    "https://www2.nzqa.govt.nz/international/"
                    "recognise-overseas-qual/iqa/"
                ),
                "supports": [
                    (
                        "NZQA owns the qualification-recognition service and "
                        "defines IQA service types and assessment scope."
                    ),
                    (
                        "Standard, Skill Shortage List, and other IQA service "
                        "types are maintained by NZQA."
                    ),
                ],
            },
            {
                "source_id": "health_nz_eligibility_direction",
                "publisher": "Health New Zealand - Te Whatu Ora",
                "title": "Health and Disability Services Eligibility",
                "url": (
                    "https://www.tewhatuora.govt.nz/assets/"
                    "Our-health-system/"
                    "Eligibility-for-publicly-funded-services/"
                    "eligibility-direction-2011.pdf"
                ),
                "supports": [
                    (
                        "Eligibility for publicly funded health services is "
                        "defined under the health-system eligibility regime, "
                        "including rules for interim and work visa holders."
                    ),
                ],
            },
        ],
        "authority_precedence": [
            {
                "rank": 1,
                "authority_class": "primary_legislation",
                "examples": ["Immigration Act 2009"],
                "rule": (
                    "Where applicable, primary legislation prevails over "
                    "subordinate regulations, instructions, and guidance."
                ),
            },
            {
                "rank": 2,
                "authority_class": "secondary_legislation",
                "examples": [
                    (
                        "Immigration (Visa, Entry Permission, and Related "
                        "Matters) Regulations 2010"
                    )
                ],
                "rule": (
                    "Regulations govern matters conferred by legislation, "
                    "including prescribed application and fee-related matters."
                ),
            },
            {
                "rank": 3,
                "authority_class": "certified_immigration_instructions",
                "examples": [
                    "Operational Manual",
                    "certified amendment awaiting incorporation",
                ],
                "rule": (
                    "Certified immigration instructions govern visa-policy "
                    "criteria and requirements subject to legislation."
                ),
            },
            {
                "rank": 4,
                "authority_class": "official_inz_non_manual_guidance",
                "examples": [
                    "Internal Administration Circulars",
                    "Advice to immigration staff / Visa Paks",
                    "INZ operational forms and guides",
                ],
                "rule": (
                    "These sources can explain procedure, administration, or "
                    "interpretation but cannot override legislation or "
                    "certified immigration instructions."
                ),
            },
            {
                "rank": 5,
                "authority_class": "responsible_external_official_authority",
                "examples": [
                    "NZQA",
                    "Health New Zealand / Ministry of Health",
                    "foreign police or issuing authority",
                    "professional registration authority",
                ],
                "rule": (
                    "These authorities own propositions within their statutory "
                    "or operational remit that are not immigration "
                    "instructions."
                ),
            },
        ],
        "proposition_source_classes": [
            {
                "source_class": "operational_manual_instruction",
                "authoritative_owner": "Immigration New Zealand",
                "authoritative_home": "Operational Manual",
                "proposition_kinds": [
                    "visa eligibility criterion",
                    "visa condition",
                    "immigration evidence requirement",
                    "immigration exception",
                    "immigration definition",
                    "immigration consequence",
                    "immigration assessment or verification rule",
                    "immigration decision criterion",
                ],
                "current_v1_if_required_but_not_indexed": "corpus_gap",
            },
            {
                "source_class": "manual_instruction_transition",
                "authoritative_owner": "Immigration New Zealand",
                "authoritative_home": (
                    "certified amendment pending or awaiting full "
                    "Operational Manual incorporation/indexing"
                ),
                "proposition_kinds": [
                    "newly certified immigration instruction",
                    "amendment to an existing immigration instruction",
                ],
                "current_v1_if_required_but_not_indexed": "corpus_gap",
                "reason": (
                    "The proposition belongs to the immigration-instruction "
                    "layer that the Operational Manual is intended to contain; "
                    "the current product has a freshness/indexing gap rather "
                    "than an external-authority proposition."
                ),
            },
            {
                "source_class": "legislation_or_regulation",
                "authoritative_owner": "New Zealand legislation",
                "authoritative_home": (
                    "Immigration Act, regulations, or other applicable law"
                ),
                "proposition_kinds": [
                    "legal power or statutory authority",
                    "application formality fixed by regulation",
                    "visa waiver fixed by regulation",
                    "prescribed fee or levy legal basis",
                    "legal rule that prevails over inconsistent instructions",
                ],
                "current_v1_if_required": "external_source_required",
                "reason": (
                    "Current Waypoint v1 is intentionally Manual-bounded. "
                    "Legislation is authoritative but outside the indexed "
                    "Manual evidence base."
                ),
            },
            {
                "source_class": "inz_live_service_information",
                "authoritative_owner": "Immigration New Zealand",
                "authoritative_home": (
                    "current INZ service page, calculator, or operational tool"
                ),
                "proposition_kinds": [
                    "current processing timeframe",
                    "current decision-time estimate",
                    "current application status",
                    "current ballot or place availability",
                    "current receiving-centre information",
                    "current application channel availability",
                ],
                "current_v1_if_required": "external_source_required",
            },
            {
                "source_class": "current_fee_or_charge_information",
                "authoritative_owner": (
                    "Immigration New Zealand and applicable regulations"
                ),
                "authoritative_home": (
                    "current INZ fee tool/guide with legal basis in "
                    "applicable regulations"
                ),
                "proposition_kinds": [
                    "current payable application fee",
                    "current levy amount",
                    "location- or citizenship-dependent current charge",
                    "current fee waiver result",
                ],
                "current_v1_if_required": "external_source_required",
            },
            {
                "source_class": "inz_non_manual_procedure_or_interpretation",
                "authoritative_owner": "Immigration New Zealand",
                "authoritative_home": (
                    "IAC, Advice to Staff, official INZ form, guide, or "
                    "non-Manual operational publication"
                ),
                "proposition_kinds": [
                    "staff administrative procedure",
                    "published interpretation guidance",
                    "operational handling detail not stated as an instruction",
                    "official form-specific procedure",
                ],
                "current_v1_if_required": "external_source_required",
                "precedence_guardrail": (
                    "May clarify but must not be used to override legislation "
                    "or certified immigration instructions."
                ),
            },
            {
                "source_class": "foreign_issuing_authority_procedure",
                "authoritative_owner": (
                    "relevant foreign police, government, or issuing authority"
                ),
                "authoritative_home": (
                    "issuing authority and, where applicable, INZ's "
                    "country-specific obtaining guidance"
                ),
                "proposition_kinds": [
                    "how to obtain a foreign police certificate",
                    "which foreign application form or option to choose",
                    "foreign document issuing procedure",
                ],
                "current_v1_if_required": "external_source_required",
            },
            {
                "source_class": "external_agency_assessment_or_service",
                "authoritative_owner": (
                    "responsible New Zealand agency or statutory body"
                ),
                "authoritative_home": "responsible agency",
                "proposition_kinds": [
                    "IQA service type",
                    "qualification-assessment process",
                    "professional registration process",
                    "external agency assessment outcome",
                ],
                "current_v1_if_required": "external_source_required",
            },
            {
                "source_class": "external_entitlement_or_service_regime",
                "authoritative_owner": (
                    "responsible public-service authority"
                ),
                "authoritative_home": (
                    "responsible statutory direction, agency, or service rules"
                ),
                "proposition_kinds": [
                    "publicly funded health eligibility",
                    "public-service entitlement",
                    "agency-administered benefit or service eligibility",
                ],
                "current_v1_if_required": "external_source_required",
            },
            {
                "source_class": "professional_or_assessor_guidance",
                "authoritative_owner": (
                    "responsible professional, clinical, registration, or "
                    "assessment authority"
                ),
                "authoritative_home": "responsible authority",
                "proposition_kinds": [
                    "clinical or assessor procedure",
                    "professional registration requirement",
                    "provider-specific procedural requirement",
                ],
                "current_v1_if_required": "external_source_required",
            },
        ],
        "generic_resolution_algorithm": [
            {
                "step": 1,
                "instruction": (
                    "Identify the exact material proposition the user requires. "
                    "Do not classify from the broad visa topic alone."
                ),
            },
            {
                "step": 2,
                "instruction": (
                    "Ask whether the proposition is an immigration rule, "
                    "criterion, condition, evidence requirement, exception, "
                    "definition, consequence, or decision rule."
                ),
                "if_yes": (
                    "Treat the authoritative domain as certified immigration "
                    "instructions, subject to legislation."
                ),
            },
            {
                "step": 3,
                "instruction": (
                    "If the proposition is instead a legal power, prescribed "
                    "regulatory requirement, or legal rule that may override "
                    "instructions, classify it as legislation/regulation."
                ),
            },
            {
                "step": 4,
                "instruction": (
                    "If the proposition is current, operational, or "
                    "time-varying service information, classify it by the "
                    "official service that maintains the current value rather "
                    "than by the visa topic."
                ),
            },
            {
                "step": 5,
                "instruction": (
                    "If the proposition concerns another agency's assessment, "
                    "entitlement, registration, issuing process, or "
                    "professional procedure, classify it to that responsible "
                    "authority."
                ),
            },
            {
                "step": 6,
                "instruction": (
                    "Do not infer external authority merely because the "
                    "retrieved Manual passages are silent."
                ),
            },
            {
                "step": 7,
                "instruction": (
                    "Do not infer a Manual corpus gap merely because the "
                    "question concerns immigration. Classify the exact "
                    "proposition's authoritative owner."
                ),
            },
        ],
        "current_waypoint_v1_status_mapping": [
            {
                "condition": (
                    "Indexed Operational Manual passages establish every "
                    "material immigration-instruction proposition needed."
                ),
                "evidence_status": "sufficient",
            },
            {
                "condition": (
                    "A required material immigration instruction belongs to "
                    "the Operational Manual / certified-instruction layer but "
                    "the indexed Manual evidence does not establish it."
                ),
                "evidence_status": "corpus_gap",
            },
            {
                "condition": (
                    "The required material proposition is authoritatively "
                    "owned outside the Operational Manual evidence base."
                ),
                "evidence_status": "external_source_required",
            },
        ],
        "boundary_examples_by_proposition_type": [
            {
                "proposition_type": (
                    "Does this visa category require a particular criterion?"
                ),
                "source_class": "operational_manual_instruction",
            },
            {
                "proposition_type": (
                    "What is the current processing time for this application?"
                ),
                "source_class": "inz_live_service_information",
            },
            {
                "proposition_type": (
                    "What fee will this applicant currently pay?"
                ),
                "source_class": "current_fee_or_charge_information",
            },
            {
                "proposition_type": (
                    "How does a foreign authority require its police "
                    "certificate application to be completed?"
                ),
                "source_class": "foreign_issuing_authority_procedure",
            },
            {
                "proposition_type": (
                    "Which NZQA qualification-assessment service applies?"
                ),
                "source_class": "external_agency_assessment_or_service",
            },
            {
                "proposition_type": (
                    "Is this person eligible for publicly funded health "
                    "services?"
                ),
                "source_class": "external_entitlement_or_service_regime",
            },
        ],
        "anti_hardcoding_and_scope_controls": [
            "No benchmark case IDs.",
            "No expected-section mappings.",
            "No gold evidence-status mappings.",
            "No visa-category-to-status lookup table.",
            "No question-string or phrase routing.",
            "No section-code-specific authority routing.",
            "No nationality-specific authority routing.",
            "No occupation-specific authority routing.",
            (
                "Classify the proposition type and responsible authority, not "
                "the topic label."
            ),
            (
                "The specification must not be interpreted as permission for "
                "unrestricted web search."
            ),
        ],
        "future_bounded_official_sources_layer": {
            "status": "DESIGN_OPTION_NOT_IMPLEMENTED",
            "principle": (
                "If Waypoint later expands beyond the Operational Manual, "
                "external retrieval must use explicit allowlisted official "
                "source families with source-type metadata and precedence."
            ),
            "candidate_source_families": [
                "New Zealand legislation",
                "INZ certified amendment circulars",
                "INZ IACs and Advice to Staff",
                "INZ current service tools and official forms/guides",
                "NZQA",
                "responsible health authority",
                "foreign issuing authorities where required",
                "professional or registration authorities where required",
            ],
            "unrestricted_web_fallback": False,
            "implementation_authorised": False,
        },
        "decisions": {
            "source_boundary_specification_frozen": True,
            "production_runtime_change_authorised": False,
            "external_source_retrieval_authorised": False,
            "unrestricted_web_search_authorised": False,
            "candidate_v7_build_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "source_boundary_classifier_design",
            "authorised": True,
            "runtime_implementation_authorised": False,
            "purpose": (
                "Design a generic classifier contract that maps an exact "
                "unsupported proposition to the frozen source classes without "
                "using benchmark examples or case-derived lookup logic."
            ),
            "precondition_for_v7": (
                "The classifier design must be frozen and independently "
                "reviewed before any candidate-v7 build can be authorised."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(specification, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("status") != (
        "FROZEN_SOURCE_ARCHITECTURE_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError("Saved specification status verification failed.")

    decisions = saved.get("decisions", {})

    if decisions.get("candidate_v7_build_authorised") is not False:
        raise RuntimeError(
            "Specification unexpectedly authorises candidate v7."
        )

    if decisions.get("external_source_retrieval_authorised") is not False:
        raise RuntimeError(
            "Specification unexpectedly authorises external retrieval."
        )

    if decisions.get("unrestricted_web_search_authorised") is not False:
        raise RuntimeError(
            "Specification unexpectedly authorises unrestricted web search."
        )

    if saved.get("next_engineering_task", {}).get(
        "runtime_implementation_authorised"
    ) is not False:
        raise RuntimeError(
            "Specification unexpectedly authorises runtime implementation."
        )

    print("Waypoint authoritative-source boundary freeze")
    print("=" * 47)
    print(f"Production v2 SHA256:      {sha256(RUNTIME_PATH)}")
    print(f"Diagnosis SHA256:          {sha256(DIAGNOSIS_PATH)}")
    print()
    print("Current product boundary:  OPERATIONAL MANUAL ONLY")
    print()
    print("Authority classes frozen")
    print("-" * 47)
    print("1. Primary legislation")
    print("2. Secondary legislation / regulations")
    print("3. Certified immigration instructions")
    print("4. Official INZ non-Manual guidance/services")
    print("5. Responsible external official authorities")
    print()
    print("Current v1 evidence mapping")
    print("-" * 47)
    print("Manual supports proposition:       sufficient")
    print("Manual-domain rule not established:corpus_gap")
    print("Authority outside Manual:          external_source_required")
    print()
    print("Certified amendment transition:    MANUAL-DOMAIN / CORPUS GAP")
    print("Live INZ service information:      EXTERNAL SOURCE")
    print("Current fee information:           EXTERNAL SOURCE")
    print("Foreign issuing procedure:         EXTERNAL SOURCE")
    print("NZQA assessment/service:           EXTERNAL SOURCE")
    print("Public-service entitlement:        EXTERNAL SOURCE")
    print()
    print("Unrestricted web fallback:         PROHIBITED")
    print("External-source retrieval:         NOT AUTHORISED")
    print("Production runtime change:         NOT AUTHORISED")
    print("Candidate v7 build:                NOT AUTHORISED")
    print("Fresh external-v3 holdout:         NOT AUTHORISED")
    print()
    print(
        "Next task:                         SOURCE-BOUNDARY "
        "CLASSIFIER DESIGN"
    )
    print("Runtime implementation:             NOT AUTHORISED")
    print()
    print(f"Output:                              {OUTPUT_PATH}")
    print(f"Boundary spec SHA256:                {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                         NONE")
    print("Retrieval/reranker calls:            NONE")
    print("Database writes:                     NONE")
    print("Runtime files modified:              NONE")
    print()
    print("Authoritative-source boundary freeze: PASS")


if __name__ == "__main__":
    main()
