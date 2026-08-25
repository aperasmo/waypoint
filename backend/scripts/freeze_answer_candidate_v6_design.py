"""Freeze the candidate-v6 answer architecture design.

This is a DESIGN-ONLY artifact.

It does not:
- modify app/api/routes/ask.py;
- create candidate-v6 runtime code;
- call retrieval, embeddings, reranking, or any model;
- read gold/evaluation cases at runtime;
- write to the database;
- authorise production promotion.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_candidate_v6_design.py
    uv run python -m scripts.freeze_answer_candidate_v6_design

Inputs:
    tests/answer_candidate_v5_rejection.json
    app/api/routes/ask.py

Output:
    tests/answer_candidate_v6_design_contract.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

V5_REJECTION_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_candidate_v5_rejection.json"
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
    / "answer_candidate_v6_design_contract.json"
)

EXPECTED_V5_REJECTION_SHA256 = (
    "BB1F372DD1533FEF5D08F27A9AF9B227"
    "AF7E5107D4071613902CA9D954163F8E"
)

EXPECTED_PRODUCTION_V2_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(
            f"{path.name}: JSON root must be an object."
        )

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"V6 design contract already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    if not V5_REJECTION_PATH.exists():
        raise SystemExit(
            f"V5 rejection artifact not found: {V5_REJECTION_PATH}"
        )

    if not RUNTIME_PATH.exists():
        raise SystemExit(
            f"Production runtime not found: {RUNTIME_PATH}"
        )

    rejection_sha = sha256(V5_REJECTION_PATH)

    if rejection_sha != EXPECTED_V5_REJECTION_SHA256:
        raise SystemExit(
            "V5 rejection SHA mismatch.\n"
            f"Expected: {EXPECTED_V5_REJECTION_SHA256}\n"
            f"Actual:   {rejection_sha}\n"
            "Refusing v6 design freeze."
        )

    runtime_sha = sha256(RUNTIME_PATH)

    if runtime_sha != EXPECTED_PRODUCTION_V2_SHA256:
        raise SystemExit(
            "Production runtime is not frozen candidate v2.\n"
            f"Expected: {EXPECTED_PRODUCTION_V2_SHA256}\n"
            f"Actual:   {runtime_sha}\n"
            "Refusing v6 design freeze."
        )

    rejection = load_json(V5_REJECTION_PATH)

    if rejection.get("schema") != (
        "waypoint-answer-candidate-v5-rejection"
    ):
        raise RuntimeError(
            "Unexpected v5 rejection schema."
        )

    if rejection.get("status") != (
        "REJECTED_DEVELOPMENT_CANDIDATE_DO_NOT_PROMOTE"
    ):
        raise RuntimeError(
            "V5 rejection status changed."
        )

    if rejection.get("decision", {}).get(
        "candidate_v5"
    ) != "REJECT":
        raise RuntimeError(
            "V5 is not recorded as rejected."
        )

    if rejection.get("decision", {}).get(
        "production_candidate"
    ) != "evidence_adequacy_v2":
        raise RuntimeError(
            "Unexpected production candidate in v5 rejection."
        )

    contract = {
        "schema": "waypoint-answer-candidate-v6-design-contract",
        "status": "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE",
        "candidate_name": "support_then_authority_then_answer_v6",
        "frozen_on": str(date.today()),
        "baseline": {
            "production_candidate": "evidence_adequacy_v2",
            "runtime_ask_sha256": EXPECTED_PRODUCTION_V2_SHA256,
        },
        "development_basis": {
            "v5_rejection_sha256": EXPECTED_V5_REJECTION_SHA256,
            "v5_decision": "REJECT",
            "retired_external_v1_v2_are_development_only": True,
            "v5_key_result": {
                "combined_v2_correct": 83,
                "combined_v2_total": 111,
                "combined_v5_correct": 81,
                "combined_v5_total": 111,
                "v5_sufficient_recall": 0.76,
                "v5_corpus_gap_recall": 60 / 68,
                "v5_external_source_required_recall": 2 / 18,
                "v5_false_sufficiency_rate": 10 / 86,
            },
        },
        "design_goal": (
            "Separate proposition support from authoritative-home resolution. "
            "First decide only whether the retrieved Operational Manual "
            "evidence establishes the material proposition. Only when support "
            "is insufficient, resolve where the missing authority properly "
            "belongs. Derive public evidence_status deterministically before "
            "answer generation."
        ),
        "experimental_hypothesis": (
            "The external_source_required failure persists because previous "
            "candidates asked one classifier to judge both evidential support "
            "and authoritative home. Factoring those into separate narrow "
            "decisions should improve authority resolution without sacrificing "
            "sufficient-case recall or recreating v4's corpus-gap collapse."
        ),
        "unchanged_system_components": [
            "Operational Manual corpus",
            "chunking",
            "embeddings",
            "PostgreSQL pgvector storage",
            "full-text search",
            "hybrid retrieval",
            "reciprocal-rank fusion",
            "retrieval top-k",
            "citation source metadata",
            "public AskRequest shape",
            "public AskResponse shape",
            "public evidence_status values",
            "public decision_boundary values",
            "legacy outcome derivation semantics",
            "disclaimer",
        ],
        "architecture": {
            "stages": [
                {
                    "stage": 1,
                    "name": "support_adjudicator",
                    "purpose": (
                        "Judge only whether the supplied Operational Manual "
                        "passages establish every material published policy "
                        "proposition needed to answer the actual question."
                    ),
                    "inputs": [
                        "user question",
                        "retrieved Operational Manual passages",
                    ],
                    "outputs": {
                        "support_status": [
                            "sufficient",
                            "insufficient",
                        ],
                        "decision_boundary": [
                            "general_information",
                            "case_specific_application",
                            "discretionary_judgement",
                        ],
                        "supporting_sections": "list[str]",
                        "missing_user_facts": "list[str]",
                        "unsupported_proposition": "string | null",
                    },
                    "must_not_do": [
                        "choose corpus_gap",
                        "choose external_source_required",
                        "classify authoritative home",
                        "generate the final user answer",
                        "use outside immigration knowledge",
                    ],
                },
                {
                    "stage": 2,
                    "name": "authority_resolver",
                    "condition": (
                        "Run only when stage-1 support_status is insufficient."
                    ),
                    "purpose": (
                        "Classify the authoritative home of the exact "
                        "unsupported proposition identified by stage 1."
                    ),
                    "inputs": [
                        "user question",
                        "retrieved Operational Manual passages",
                        "stage-1 unsupported_proposition",
                    ],
                    "outputs": {
                        "authoritative_home": [
                            "operational_manual",
                            "external_authority",
                        ],
                        "authority_kind": [
                            "manual_instruction_or_definition",
                            "live_service_information",
                            "separate_fee_or_charge_schedule",
                            "external_issuing_authority_procedure",
                            "external_agency_service_or_assessment",
                            "external_entitlement_or_organisation_definition",
                            "professional_or_assessor_guidance",
                            "other_external_authority",
                        ],
                        "authority_rationale": "string",
                    },
                    "must_not_do": [
                        "change stage-1 support_status",
                        "change stage-1 unsupported_proposition",
                        "generate the final user answer",
                        "route by visa category",
                        "route by benchmark question",
                    ],
                },
                {
                    "stage": 3,
                    "name": "answer_generator",
                    "purpose": (
                        "Generate the user-facing answer from the retrieved "
                        "Manual evidence and the already-fixed internal "
                        "adjudication."
                    ),
                    "inputs": [
                        "user question",
                        "retrieved Operational Manual passages",
                        "derived evidence_status",
                        "stage-1 decision_boundary",
                        "stage-1 supporting_sections",
                        "stage-1 missing_user_facts",
                        "stage-1 unsupported_proposition",
                        "stage-2 authoritative_home when applicable",
                        "stage-2 authority_kind when applicable",
                    ],
                    "outputs": {
                        "answer": "string",
                        "cited_sections": "list[str]",
                        "missing_information": "list[str]",
                    },
                    "cannot_override": [
                        "derived evidence_status",
                        "stage-1 decision_boundary",
                        "stage-1 missing_user_facts",
                    ],
                },
            ],
            "conditional_model_calls": {
                "support_sufficient": 2,
                "support_insufficient": 3,
                "note": (
                    "Support-sufficient cases skip the authority resolver. "
                    "The answer generator always runs after evidence_status "
                    "has already been fixed."
                ),
            },
        },
        "deterministic_status_derivation": {
            "mapping": [
                {
                    "when": {
                        "support_status": "sufficient",
                    },
                    "evidence_status": "sufficient",
                },
                {
                    "when": {
                        "support_status": "insufficient",
                        "authoritative_home": "operational_manual",
                    },
                    "evidence_status": "corpus_gap",
                },
                {
                    "when": {
                        "support_status": "insufficient",
                        "authoritative_home": "external_authority",
                    },
                    "evidence_status": "external_source_required",
                },
            ],
            "generic_only": True,
            "contains_immigration_topic_rules": False,
            "contains_section_specific_rules": False,
            "contains_benchmark_rules": False,
        },
        "stage_1_support_contract": {
            "sufficient": (
                "Use only when the retrieved passages establish every "
                "material published policy proposition required to answer the "
                "actual question within the applicable scope. Support may be "
                "direct, composed across compatible passages without an "
                "unsupported bridge, or established by a genuinely closed or "
                "exhaustive rule."
            ),
            "insufficient": (
                "Use whenever at least one material published policy "
                "proposition needed for the actual question is not established "
                "by the supplied passages."
            ),
            "rules": [
                (
                    "Do not treat topic similarity, related headings, adjacent "
                    "rules, analogous categories, or general objectives as "
                    "support for a proposition they do not establish."
                ),
                (
                    "Do not transfer scope across visa category, pathway, "
                    "application type, decision stage, person type, evidence "
                    "type, or procedure unless the supplied text expressly "
                    "gives the rule broader scope."
                ),
                (
                    "Do not infer categorical negatives from silence unless "
                    "the applicable retrieved rule is closed or exhaustive "
                    "for the exact issue."
                ),
                (
                    "Missing user facts do not make published evidence "
                    "insufficient when the governing rule itself is fully "
                    "established."
                ),
            ],
        },
        "stage_2_authority_contract": {
            "operational_manual": (
                "Choose when the unsupported proposition is itself an "
                "immigration instruction, criterion, visa condition, evidence "
                "requirement, consequence, operative procedure, exception, "
                "definition, delegated Manual appendix/table/list, or other "
                "published rule whose authoritative home is the Operational "
                "Manual."
            ),
            "external_authority": (
                "Choose when the unsupported proposition is authoritatively "
                "maintained outside the Operational Manual, including live "
                "service information, separate fee or charge schedules, "
                "foreign issuing-authority procedures, another agency's "
                "assessment/service, an external organisation's entitlement "
                "definition, or professional/assessor guidance not supplied "
                "by the Manual."
            ),
            "rules": [
                (
                    "The resolver classifies the authoritative home of the "
                    "unsupported proposition, not the broad topic of the "
                    "question."
                ),
                (
                    "Absence from retrieved passages does not prove external "
                    "authority."
                ),
                (
                    "An external classification must be justified by the "
                    "nature of the requested proposition or an explicit "
                    "delegation in supplied Manual evidence."
                ),
                (
                    "If the missing proposition is an immigration rule that "
                    "would ordinarily be expressed as an instruction, "
                    "condition, criterion, exception, definition, or operative "
                    "procedure, classify it as operational_manual even when "
                    "the relevant Manual content is not indexed."
                ),
                (
                    "authority_kind is diagnostic structure only and must not "
                    "be used as a topic-specific shortcut to the public "
                    "evidence_status."
                ),
            ],
        },
        "decision_boundary_contract": {
            "general_information": (
                "The published rule can be explained without a material "
                "unstated personal fact determining which rule, branch, "
                "threshold, condition, or exception applies."
            ),
            "case_specific_application": (
                "The user asks what follows for their situation and at least "
                "one unstated personal or situational fact materially "
                "determines which published rule, branch, threshold, "
                "condition, or exception applies."
            ),
            "discretionary_judgement": (
                "Even with all relevant personal facts known, the requested "
                "result centrally depends on qualitative or discretionary "
                "judgement by an authorised decision-maker."
            ),
        },
        "answer_generation_contract": [
            (
                "The answer generator receives evidence_status as immutable "
                "input and cannot recalculate or override it."
            ),
            (
                "For sufficient, answer from retrieved Manual evidence only "
                "and preserve material scope, conditions, and exceptions."
            ),
            (
                "For corpus_gap, do not invent the missing Manual rule."
            ),
            (
                "For external_source_required, do not guess the external "
                "value, procedure, entitlement, assessment, or guidance."
            ),
            (
                "cited_sections may contain only retrieved section codes that "
                "materially support claims in the final answer."
            ),
            (
                "missing_information must contain only stage-1 missing user "
                "facts and never missing policy or external sources."
            ),
        ],
        "failure_handling_contract": {
            "stage_1_malformed_output": (
                "Fail explicitly. Do not silently substitute support status."
            ),
            "stage_2_malformed_output": (
                "For insufficient cases, fail explicitly. Do not silently "
                "substitute authoritative home."
            ),
            "stage_3_malformed_output": (
                "Fail explicitly. Do not silently fabricate an answer."
            ),
            "no_default_support_status": True,
            "no_default_authoritative_home": True,
            "no_keyword_fallback_classifier": True,
        },
        "public_api_contract": {
            "request_shape_changed": False,
            "response_shape_changed": False,
            "fields": [
                "question",
                "interpreted_as",
                "outcome",
                "evidence_status",
                "decision_boundary",
                "answer",
                "citations",
                "missing_information",
                "disclaimer",
            ],
            "internal_stage_fields_exposed_publicly": False,
        },
        "anti_hardcoding_rules": [
            "No benchmark case IDs in any stage.",
            "No exact or partial benchmark-question routing.",
            "No expected-section mappings.",
            "No gold evidence-status mappings.",
            "No adjudication-note text imported into runtime.",
            "No section-code-specific support or authority logic.",
            "No visa-category-specific support or authority lookup tables.",
            "No topic-keyword rules that directly force support status, authoritative home, or evidence status.",
            "No runtime import or read of tests, gold, taxonomy, failure inventory, or evaluation artifacts.",
            "No benchmark-specific few-shot examples.",
            "No question-specific routing between stages.",
            "The authority resolver runs only because support is insufficient, never because of topic identity.",
            "The answer generator cannot override the derived evidence status.",
            "Only generic semantic evidence and authority rules are allowed.",
        ],
        "candidate_build_constraints": [
            (
                "Candidate v6 must be built outside app/ and must not replace "
                "the frozen v2 production runtime during development."
            ),
            (
                "Retired external v1 and v2 may be used only as development "
                "and diagnostic data."
            ),
            (
                "Both retired prediction sets must be generated before "
                "candidate-v6 scores are inspected."
            ),
            (
                "No candidate modification may occur between the retired-v1 "
                "and retired-v2 prediction runs."
            ),
            (
                "Candidate-v6 development results cannot be described as "
                "fresh generalisation evidence."
            ),
            (
                "If candidate v6 is selected, fresh external-v3 acceptance "
                "criteria must be frozen before the first prediction."
            ),
            (
                "Fresh external-v3 must be collected and adjudicated without "
                "seeing candidate-v6 outputs."
            ),
        ],
        "evaluation_focus": {
            "primary": [
                "overall evidence-status accuracy",
                "sufficient recall",
                "corpus_gap recall",
                "external_source_required recall",
                "false-sufficiency rate among non-sufficient gold cases",
            ],
            "secondary": [
                "citation coverage on sufficient cases",
                "source-cluster macro accuracy where applicable",
                "support-adjudicator malformed-output rate",
                "authority-resolver malformed-output rate",
                "answer-generator malformed-output rate",
                "conditional model-call distribution",
            ],
            "development_comparator": "frozen candidate v2",
        },
        "promotion_authority": {
            "candidate_v6_build_authorised": True,
            "runtime_replacement_authorised": False,
            "production_promotion_authorised": False,
            "fresh_holdout_run_authorised": False,
            "fresh_holdout_generalisation_claim_authorised": False,
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(contract, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    verify = load_json(OUTPUT_PATH)

    if verify.get("status") != (
        "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE"
    ):
        raise RuntimeError(
            "Saved v6 design status verification failed."
        )

    authority = verify.get("promotion_authority", {})

    if authority.get("candidate_v6_build_authorised") is not True:
        raise RuntimeError(
            "Saved v6 design does not authorise candidate build."
        )

    if authority.get("runtime_replacement_authorised") is not False:
        raise RuntimeError(
            "V6 design unexpectedly authorises runtime replacement."
        )

    if verify.get(
        "baseline", {}
    ).get("runtime_ask_sha256") != EXPECTED_PRODUCTION_V2_SHA256:
        raise RuntimeError(
            "Saved baseline runtime linkage verification failed."
        )

    print("Waypoint candidate-v6 design contract freeze")
    print("=" * 45)
    print(f"V5 rejection SHA256:       {rejection_sha}")
    print(f"Production v2 SHA256:      {runtime_sha}")
    print()
    print("Architecture:               FACTORISED THREE-PART")
    print("Stage 1:                    SUPPORT ADJUDICATOR")
    print("Stage 2:                    AUTHORITY RESOLVER")
    print("Stage 3:                    ANSWER GENERATOR")
    print("Public API shape changed:   NO")
    print("Retrieval changed:          NO")
    print("Production runtime changed: NO")
    print()
    print("Status derivation:          DETERMINISTIC / GENERIC")
    print("Benchmark hardcoding:       PROHIBITED")
    print("Section-specific routing:   PROHIBITED")
    print("Visa-specific status map:   PROHIBITED")
    print("Runtime eval-data access:   PROHIBITED")
    print("Answer status override:     PROHIBITED")
    print()
    print("Candidate-v6 build:         AUTHORISED")
    print("Runtime replacement:        NOT AUTHORISED")
    print("Fresh holdout run:          NOT AUTHORISED")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Design contract SHA256:     {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Candidate-v6 design contract freeze: PASS")


if __name__ == "__main__":
    main()
