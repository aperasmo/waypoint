"""Freeze the candidate-v5 two-stage answer architecture design.

This is a DESIGN-ONLY artifact.

It does not:
- modify app/api/routes/ask.py;
- create candidate-v5 runtime code;
- call retrieval, embeddings, reranking, or any model;
- read gold/evaluation cases at runtime;
- write to the database;
- authorise production promotion.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_candidate_v5_design.py
    uv run python -m scripts.freeze_answer_candidate_v5_design

Inputs:
    tests/answer_candidate_v4_rejection.json
    app/api/routes/ask.py

Output:
    tests/answer_candidate_v5_design_contract.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

V4_REJECTION_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_candidate_v4_rejection.json"
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
    / "answer_candidate_v5_design_contract.json"
)

EXPECTED_V4_REJECTION_SHA256 = (
    "1C8891FE69F63D416D49AC8A3106EC604551D5EBF0EFDF4266B8E522F837C432"
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
            f"V5 design contract already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    if not V4_REJECTION_PATH.exists():
        raise SystemExit(
            f"V4 rejection artifact not found: {V4_REJECTION_PATH}"
        )

    if not RUNTIME_PATH.exists():
        raise SystemExit(
            f"Production runtime not found: {RUNTIME_PATH}"
        )

    rejection_sha = sha256(V4_REJECTION_PATH)

    if rejection_sha != EXPECTED_V4_REJECTION_SHA256:
        raise SystemExit(
            "V4 rejection SHA mismatch.\n"
            f"Expected: {EXPECTED_V4_REJECTION_SHA256}\n"
            f"Actual:   {rejection_sha}\n"
            "Refusing v5 design freeze."
        )

    runtime_sha = sha256(RUNTIME_PATH)

    if runtime_sha != EXPECTED_PRODUCTION_V2_SHA256:
        raise SystemExit(
            "Production runtime is not frozen candidate v2.\n"
            f"Expected: {EXPECTED_PRODUCTION_V2_SHA256}\n"
            f"Actual:   {runtime_sha}\n"
            "Refusing v5 design freeze."
        )

    rejection = load_json(V4_REJECTION_PATH)

    if rejection.get("schema") != (
        "waypoint-answer-candidate-v4-rejection"
    ):
        raise RuntimeError(
            "Unexpected v4 rejection schema."
        )

    if rejection.get("status") != (
        "REJECTED_DEVELOPMENT_CANDIDATE_DO_NOT_PROMOTE"
    ):
        raise RuntimeError(
            "V4 rejection status changed."
        )

    if rejection.get("decision", {}).get(
        "candidate_v4"
    ) != "REJECT":
        raise RuntimeError(
            "V4 is not recorded as rejected."
        )

    if rejection.get("decision", {}).get(
        "production_candidate"
    ) != "evidence_adequacy_v2":
        raise RuntimeError(
            "Unexpected production candidate in v4 rejection."
        )

    contract = {
        "schema": "waypoint-answer-candidate-v5-design-contract",
        "status": "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE",
        "candidate_name": "two_stage_evidence_then_answer_v5",
        "frozen_on": str(date.today()),
        "baseline": {
            "production_candidate": "evidence_adequacy_v2",
            "runtime_ask_sha256": EXPECTED_PRODUCTION_V2_SHA256,
        },
        "development_basis": {
            "v4_rejection_sha256": EXPECTED_V4_REJECTION_SHA256,
            "v4_decision": "REJECT",
            "retired_external_v1_v2_are_development_only": True,
            "v4_key_result": {
                "combined_v2_correct": 83,
                "combined_v2_total": 111,
                "combined_v4_correct": 76,
                "combined_v4_total": 111,
                "v4_sufficient_recall": 0.24,
                "v4_corpus_gap_recall": 1.0,
                "v4_external_source_required_recall": (
                    0.1111111111111111
                ),
                "v4_false_sufficiency_rate": 0.0,
            },
        },
        "design_goal": (
            "Separate evidence-status adjudication from answer generation so "
            "the classification is made by a narrow structured first stage "
            "before any natural-language answer is written."
        ),
        "experimental_hypothesis": (
            "A dedicated evidence adjudicator can retain the reduction in "
            "false-sufficiency observed in v4 without the severe corpus-gap "
            "bias caused when classification and answer formulation were "
            "performed in a single model response."
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
                    "name": "evidence_adjudicator",
                    "purpose": (
                        "Classify whether the retrieved Operational Manual "
                        "evidence is sufficient for the actual proposition, "
                        "and if not, whether the missing authority belongs in "
                        "the Manual or outside it."
                    ),
                    "must_not_generate": [
                        "final user answer",
                        "immigration recommendation",
                        "eligibility decision for a person",
                        "invented policy content",
                    ],
                    "inputs": [
                        "user question",
                        "retrieved Operational Manual passages",
                    ],
                    "outputs": {
                        "evidence_status": [
                            "sufficient",
                            "corpus_gap",
                            "external_source_required",
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
                },
                {
                    "stage": 2,
                    "name": "answer_generator",
                    "purpose": (
                        "Generate the user-facing answer using the retrieved "
                        "Manual evidence and the already-fixed adjudication "
                        "from stage 1."
                    ),
                    "inputs": [
                        "user question",
                        "retrieved Operational Manual passages",
                        "stage-1 evidence_status",
                        "stage-1 decision_boundary",
                        "stage-1 supporting_sections",
                        "stage-1 missing_user_facts",
                        "stage-1 unsupported_proposition",
                    ],
                    "outputs": {
                        "answer": "string",
                        "cited_sections": "list[str]",
                        "missing_information": "list[str]",
                    },
                    "cannot_override": [
                        "stage-1 evidence_status",
                        "stage-1 decision_boundary",
                    ],
                },
            ],
            "public_response_assembly": (
                "The API assembles the existing AskResponse from the stage-1 "
                "classification, the stage-2 answer fields, retrieved citation "
                "metadata, the existing outcome derivation, and disclaimer."
            ),
        },
        "stage_1_evidence_contract": {
            "sufficient": (
                "Use only when the retrieved passages establish every "
                "material policy proposition needed to answer the actual "
                "question within the applicable scope. Support may come from "
                "one passage or multiple compatible passages. A genuinely "
                "closed or exhaustive rule may establish a negative answer."
            ),
            "corpus_gap": (
                "Use when a material proposition is not established by the "
                "retrieved evidence and the authoritative home of that "
                "missing proposition is the Operational Manual, including an "
                "absent Manual section, appendix, table, instruction, "
                "exception, definition, or operative procedure."
            ),
            "external_source_required": (
                "Use when a material proposition needed to answer the "
                "question is authoritatively maintained outside the "
                "Operational Manual, such as live service information, a "
                "separate fee or charge schedule, an external issuing "
                "authority's procedure, another agency's assessment or "
                "service, an external organisation's entitlement definition, "
                "or professional/assessor guidance not supplied by the Manual."
            ),
        },
        "stage_1_reasoning_invariants": [
            (
                "Topic similarity, a related heading, a neighbouring rule, "
                "or a rule about a different category is not sufficient "
                "evidence for the requested proposition."
            ),
            (
                "A rule may be composed across multiple passages only when "
                "their scopes are compatible and no unsupported bridging "
                "assumption is needed."
            ),
            (
                "A categorical negative may not be inferred from silence "
                "unless the applicable retrieved rule is closed or exhaustive "
                "for the exact issue."
            ),
            (
                "A general rule may answer a narrower case when the retrieved "
                "text expressly includes that case and no material "
                "category-specific rule is missing."
            ),
            (
                "The absence of a rule from the retrieved passages does not "
                "by itself establish external_source_required."
            ),
            (
                "External-source classification requires a reason grounded in "
                "the nature or explicit delegation of the missing authority, "
                "not a topic keyword."
            ),
            (
                "supporting_sections may contain only section codes present "
                "in the retrieved evidence."
            ),
            (
                "missing_user_facts may contain only personal or situational "
                "facts about the user or case. It must not contain missing "
                "policy, sections, appendices, tables, external services, or "
                "authoritative guidance."
            ),
        ],
        "decision_boundary_contract": {
            "general_information": (
                "The published rule can be explained without a material "
                "unstated personal fact determining which rule, branch, "
                "threshold, condition, or exception applies."
            ),
            "case_specific_application": (
                "The user asks what follows for their situation and at least "
                "one unstated personal fact materially determines which "
                "published rule, branch, threshold, condition, or exception "
                "applies."
            ),
            "discretionary_judgement": (
                "Even if relevant personal facts were known, the requested "
                "result centrally depends on qualitative or discretionary "
                "judgement by an authorised decision-maker."
            ),
        },
        "stage_2_answer_contract": [
            (
                "Stage 2 must treat stage-1 evidence_status and "
                "decision_boundary as immutable inputs."
            ),
            (
                "For sufficient, answer the actual question using only "
                "retrieved Manual evidence and preserve material conditions "
                "and exceptions."
            ),
            (
                "For corpus_gap, explain established relevant evidence only "
                "when useful and identify the unsupported Manual proposition "
                "without inventing its content."
            ),
            (
                "For external_source_required, explain any established Manual "
                "context and identify the kind of external authoritative "
                "source required without guessing its content."
            ),
            (
                "The answer must not state a stronger proposition than the "
                "retrieved evidence and stage-1 adjudication permit."
            ),
            (
                "cited_sections may contain only retrieved section codes that "
                "materially support claims in the final answer."
            ),
            (
                "missing_information must contain only stage-1 missing user "
                "facts. It must not contain missing policy or external "
                "sources."
            ),
        ],
        "failure_handling_contract": {
            "stage_1_malformed_output": (
                "Candidate evaluation must fail explicitly rather than "
                "silently substituting an evidence status."
            ),
            "stage_2_malformed_output": (
                "Candidate evaluation must fail explicitly rather than "
                "silently fabricating an answer."
            ),
            "no_default_status": True,
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
            "stage_1_internal_fields_exposed_publicly": False,
        },
        "anti_hardcoding_rules": [
            "No benchmark case IDs in either stage.",
            "No exact or partial benchmark-question routing.",
            "No expected-section mappings in either stage.",
            "No gold evidence-status mappings in either stage.",
            "No adjudication-note text imported into either stage.",
            "No section-code-specific evidence-status logic.",
            "No visa-category-specific evidence-status lookup tables.",
            "No topic-keyword rules that directly force an evidence status.",
            "No runtime import or read of tests, gold, taxonomy, failure inventory, or evaluation artifacts.",
            "No benchmark-specific few-shot examples.",
            "No question-specific routing between stages.",
            "Stage 2 cannot recalculate or override the stage-1 evidence status.",
            "Only generic semantic evidence rules are allowed.",
        ],
        "candidate_build_constraints": [
            (
                "Candidate v5 must be built outside app/ and must not replace "
                "the frozen v2 production runtime during development."
            ),
            (
                "The initial candidate comparison may use retired external "
                "v1 and v2 only as development/diagnostic data."
            ),
            (
                "Both retired development prediction sets must be generated "
                "before inspecting candidate-v5 scores."
            ),
            (
                "No candidate modification may occur between running retired "
                "v1 and retired v2 predictions."
            ),
            (
                "Candidate-v5 development results cannot be described as "
                "fresh generalisation evidence."
            ),
            (
                "If candidate v5 is selected, acceptance criteria must be "
                "frozen before the first prediction on a fresh external-v3 "
                "holdout."
            ),
            (
                "The fresh external-v3 holdout must be collected and "
                "adjudicated without seeing candidate-v5 outputs."
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
                "stage-1 malformed-output rate",
                "stage-2 malformed-output rate",
            ],
            "development_comparator": "frozen candidate v2",
        },
        "promotion_authority": {
            "candidate_v5_build_authorised": True,
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
            "Saved v5 design status verification failed."
        )

    if verify.get(
        "promotion_authority", {}
    ).get("candidate_v5_build_authorised") is not True:
        raise RuntimeError(
            "Saved v5 design does not authorise candidate build."
        )

    if verify.get(
        "promotion_authority", {}
    ).get("runtime_replacement_authorised") is not False:
        raise RuntimeError(
            "V5 design unexpectedly authorises runtime replacement."
        )

    if verify.get(
        "baseline", {}
    ).get("runtime_ask_sha256") != EXPECTED_PRODUCTION_V2_SHA256:
        raise RuntimeError(
            "Saved baseline runtime linkage verification failed."
        )

    print("Waypoint candidate-v5 design contract freeze")
    print("=" * 45)
    print(f"V4 rejection SHA256:       {rejection_sha}")
    print(f"Production v2 SHA256:      {runtime_sha}")
    print()
    print("Architecture:               TWO STAGE")
    print("Stage 1:                    EVIDENCE ADJUDICATOR")
    print("Stage 2:                    ANSWER GENERATOR")
    print("Public API shape changed:   NO")
    print("Retrieval changed:          NO")
    print("Production runtime changed: NO")
    print()
    print("Benchmark hardcoding:       PROHIBITED")
    print("Section-specific routing:   PROHIBITED")
    print("Topic-specific status map:  PROHIBITED")
    print("Runtime eval-data access:   PROHIBITED")
    print("Stage-2 status override:    PROHIBITED")
    print()
    print("Candidate-v5 build:         AUTHORISED")
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
    print("Candidate-v5 design contract freeze: PASS")


if __name__ == "__main__":
    main()
