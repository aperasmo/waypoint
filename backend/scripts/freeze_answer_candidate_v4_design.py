"""Freeze the candidate-v4 answer-layer design contract.

This artifact defines the architecture of candidate v4 before any candidate
runtime code is written.

It DOES NOT:
- modify app/api/routes/ask.py;
- import evaluation data into runtime;
- call the answer model;
- call retrieval, embeddings, or reranking;
- write to the database;
- authorise production promotion.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_candidate_v4_design.py
    uv run python -m scripts.freeze_answer_candidate_v4_design

Inputs:
    tests/answer_failure_taxonomy_candidate_v2_frozen.json
    app/api/routes/ask.py

Output:
    tests/answer_candidate_v4_design_contract.json
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

TAXONOMY_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_failure_taxonomy_candidate_v2_frozen.json"
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
    / "answer_candidate_v4_design_contract.json"
)

EXPECTED_TAXONOMY_SHA256 = (
    "0AB84EB3A83F6B97A2CBBA603C6D5304"
    "19E93A07DC6E8671183462E17DA5BCB9"
)

EXPECTED_BASELINE_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_PRIMARY_COUNTS = {
    "authoritative_home_resolution_failure": 13,
    "scope_entailment_overreach": 11,
    "scope_entailment_underreach": 4,
}


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
            f"V4 design contract already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    if not TAXONOMY_PATH.exists():
        raise SystemExit(
            f"Frozen taxonomy not found: {TAXONOMY_PATH}"
        )

    if not RUNTIME_PATH.exists():
        raise SystemExit(
            f"Baseline runtime not found: {RUNTIME_PATH}"
        )

    taxonomy_sha = sha256(TAXONOMY_PATH)

    if taxonomy_sha != EXPECTED_TAXONOMY_SHA256:
        raise SystemExit(
            "Frozen taxonomy SHA mismatch.\n"
            f"Expected: {EXPECTED_TAXONOMY_SHA256}\n"
            f"Actual:   {taxonomy_sha}\n"
            "Refusing v4 design freeze."
        )

    runtime_sha = sha256(RUNTIME_PATH)

    if runtime_sha != EXPECTED_BASELINE_RUNTIME_SHA256:
        raise SystemExit(
            "Baseline runtime is not frozen candidate v2.\n"
            f"Expected: {EXPECTED_BASELINE_RUNTIME_SHA256}\n"
            f"Actual:   {runtime_sha}\n"
            "Refusing v4 design freeze."
        )

    taxonomy = load_json(TAXONOMY_PATH)

    if taxonomy.get("schema") != (
        "waypoint-answer-failure-taxonomy-candidate-v2-frozen"
    ):
        raise RuntimeError(
            "Unexpected frozen taxonomy schema."
        )

    if taxonomy.get("status") != (
        "FROZEN_DEVELOPMENT_DESIGN_BASIS_DO_NOT_USE_AS_RUNTIME"
    ):
        raise RuntimeError(
            "Frozen taxonomy status changed."
        )

    if taxonomy.get("failure_count") != 28:
        raise RuntimeError(
            "Expected 28 frozen taxonomy failures."
        )

    if taxonomy.get(
        "primary_mechanism_counts"
    ) != EXPECTED_PRIMARY_COUNTS:
        raise RuntimeError(
            "Frozen taxonomy primary counts changed."
        )

    contract = {
        "schema": "waypoint-answer-candidate-v4-design-contract",
        "status": "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE",
        "candidate_name": "factorised_evidence_adjudication_v4",
        "frozen_on": str(date.today()),
        "baseline": {
            "candidate": "evidence_adequacy_v2",
            "runtime_ask_sha256": EXPECTED_BASELINE_RUNTIME_SHA256,
        },
        "development_basis": {
            "frozen_taxonomy_sha256": EXPECTED_TAXONOMY_SHA256,
            "taxonomy_failure_count": 28,
            "primary_mechanism_counts": EXPECTED_PRIMARY_COUNTS,
            "retired_external_v1_v2_are_development_only": True,
        },
        "design_goal": (
            "Separate evidence-support assessment from authoritative-home "
            "assessment, then derive the public evidence_status through "
            "generic deterministic logic."
        ),
        "unchanged_system_components": [
            "corpus",
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
            "decision_boundary public semantics",
            "disclaimer",
        ],
        "model_inputs": [
            "user question",
            "retrieved Operational Manual passages",
        ],
        "internal_model_contract": {
            "evidence_support": {
                "allowed_values": [
                    "direct",
                    "composed",
                    "closed_rule",
                    "partial",
                    "none",
                ],
                "definitions": {
                    "direct": (
                        "The retrieved evidence directly establishes every "
                        "material proposition needed to answer the question "
                        "within the applicable scope."
                    ),
                    "composed": (
                        "Every material proposition is established by a "
                        "combination of retrieved passages with compatible "
                        "scope, and no unsupported bridging assumption is "
                        "required."
                    ),
                    "closed_rule": (
                        "An applicable closed or exhaustive rule establishes "
                        "the answer by inclusion or exclusion, including a "
                        "negative conclusion where the rule is genuinely "
                        "exhaustive."
                    ),
                    "partial": (
                        "The retrieved evidence is relevant but at least one "
                        "material proposition remains unsupported, or there "
                        "is a material scope, category, stage, evidence-type, "
                        "procedure, or exception gap."
                    ),
                    "none": (
                        "The retrieved evidence does not materially establish "
                        "the proposition required to answer the question."
                    ),
                },
            },
            "authoritative_home": {
                "allowed_values": [
                    "operational_manual",
                    "external_authority",
                    "not_applicable",
                ],
                "definitions": {
                    "operational_manual": (
                        "A material unsupported proposition is an immigration "
                        "instruction, eligibility criterion, visa condition, "
                        "evidence requirement, application consequence, "
                        "operative procedure, exception, or definition whose "
                        "authoritative home is the Operational Manual, "
                        "including material explicitly delegated to another "
                        "Manual section, appendix, or table that is absent "
                        "from the indexed corpus."
                    ),
                    "external_authority": (
                        "A material unsupported proposition is authoritatively "
                        "maintained outside the Operational Manual, such as "
                        "live or changeable service information, a separate "
                        "fee or charge schedule, an issuing authority's "
                        "procedure, another agency's assessment or service, "
                        "an external organisation's eligibility definition, "
                        "or professional/assessor guidance that the Manual "
                        "does not itself supply."
                    ),
                    "not_applicable": (
                        "No material proposition required for the answer "
                        "remains unsupported by the retrieved Manual evidence."
                    ),
                },
            },
            "decision_boundary": {
                "allowed_values": [
                    "general_information",
                    "case_specific_application",
                    "discretionary_judgement",
                ],
                "semantics": "Preserve candidate-v2 public semantics.",
            },
            "answer": {
                "type": "string",
                "rule": (
                    "Must be consistent with evidence_support and may not "
                    "state a stronger proposition than the retrieved evidence "
                    "supports."
                ),
            },
            "cited_sections": {
                "type": "list[str]",
                "rule": (
                    "May cite only section codes present in the retrieved "
                    "evidence supplied to the model."
                ),
            },
            "missing_information": {
                "type": "list[str]",
                "rule": (
                    "May contain only missing user facts needed to apply an "
                    "otherwise established rule. It must not contain missing "
                    "policy, sections, appendices, tables, external sources, "
                    "service information, or authoritative guidance."
                ),
            },
        },
        "generic_reasoning_invariants": [
            (
                "A result may be sufficient only when evidence_support is "
                "direct, composed, or closed_rule."
            ),
            (
                "Partial relevance is never sufficient evidence for the "
                "unanswered material proposition."
            ),
            (
                "A rule from a different visa category, pathway, application "
                "type, decision stage, person type, evidence type, or "
                "procedure may not be transferred unless the retrieved text "
                "expressly gives it broader scope."
            ),
            (
                "A general rule may support a narrower case when the text's "
                "scope expressly includes that case and no material "
                "category-specific rule is missing."
            ),
            (
                "A categorical conclusion may not be inferred merely because "
                "the retrieved passages do not mention an alternative."
            ),
            (
                "A negative conclusion from absence is allowed only when an "
                "applicable rule is closed or exhaustive for the exact "
                "question being decided."
            ),
            (
                "If the answer text acknowledges that a material proposition "
                "is not established by the supplied evidence, "
                "evidence_support must be partial or none."
            ),
            (
                "authoritative_home is assessed only for material unsupported "
                "propositions. It is not a topic classifier."
            ),
            (
                "The absence of a rule from retrieved passages does not by "
                "itself prove that the rule belongs outside the Operational "
                "Manual."
            ),
            (
                "Explicit delegation by the Manual to another authority, "
                "service, guideline, schedule, or issuing body may support "
                "external_authority when the delegated material is needed to "
                "answer the question."
            ),
        ],
        "deterministic_public_mapping": {
            "rules": [
                {
                    "when": {
                        "evidence_support": [
                            "direct",
                            "composed",
                            "closed_rule",
                        ]
                    },
                    "evidence_status": "sufficient",
                },
                {
                    "when": {
                        "evidence_support": [
                            "partial",
                            "none",
                        ],
                        "authoritative_home": "external_authority",
                    },
                    "evidence_status": "external_source_required",
                },
                {
                    "when": {
                        "evidence_support": [
                            "partial",
                            "none",
                        ],
                        "authoritative_home": [
                            "operational_manual",
                            "not_applicable",
                        ],
                    },
                    "evidence_status": "corpus_gap",
                },
            ],
            "note": (
                "The mapping contains no immigration topic, question, "
                "section, benchmark, or expected-answer logic."
            ),
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
            "internal_v4_fields_exposed_publicly": False,
        },
        "anti_hardcoding_rules": [
            "No benchmark case IDs in runtime code or prompts.",
            "No exact or partial benchmark-question routing.",
            "No expected-section mappings in runtime code or prompts.",
            "No gold evidence-status mappings in runtime code or prompts.",
            "No adjudication-note text imported into runtime code or prompts.",
            "No section-code-specific evidence-status logic.",
            "No visa-category-specific evidence-status lookup tables.",
            "No topic-keyword rules that directly force an evidence status.",
            "No runtime import or read of tests, gold, taxonomy, or evaluation artifacts.",
            "No benchmark-specific few-shot examples.",
            "Only generic semantic definitions and generic deterministic contract logic are allowed.",
        ],
        "candidate_build_constraints": [
            (
                "Candidate v4 must be created outside app/ first and must not "
                "replace the frozen v2 runtime during development."
            ),
            (
                "The initial candidate comparison may use retired external "
                "v1 and v2 only as development/diagnostic data."
            ),
            (
                "A candidate-v4 development improvement cannot be described "
                "as fresh generalisation evidence."
            ),
            (
                "If candidate v4 is selected for a fresh holdout, acceptance "
                "criteria must be frozen before the first fresh prediction "
                "run."
            ),
            (
                "A fresh external holdout must be collected and adjudicated "
                "without seeing candidate-v4 outputs."
            ),
        ],
        "promotion_authority": {
            "candidate_code_authorised": True,
            "runtime_replacement_authorised": False,
            "production_promotion_authorised": False,
            "fresh_holdout_generalisation_claim_authorised": False,
        },
    }

    serialised = json.dumps(
        contract,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    OUTPUT_PATH.write_text(
        serialised,
        encoding="utf-8",
    )

    verify = load_json(OUTPUT_PATH)

    if verify.get("status") != "FROZEN_DESIGN_ONLY_NO_RUNTIME_CHANGE":
        raise RuntimeError(
            "Saved v4 design status verification failed."
        )

    if verify.get(
        "development_basis", {}
    ).get("frozen_taxonomy_sha256") != EXPECTED_TAXONOMY_SHA256:
        raise RuntimeError(
            "Saved taxonomy linkage verification failed."
        )

    if verify.get(
        "baseline", {}
    ).get("runtime_ask_sha256") != EXPECTED_BASELINE_RUNTIME_SHA256:
        raise RuntimeError(
            "Saved baseline runtime linkage verification failed."
        )

    if verify.get(
        "promotion_authority", {}
    ).get("runtime_replacement_authorised") is not False:
        raise RuntimeError(
            "Design contract unexpectedly authorises runtime replacement."
        )

    print("Waypoint candidate-v4 design contract freeze")
    print("=" * 44)
    print(f"Frozen taxonomy:            {TAXONOMY_PATH}")
    print(f"Taxonomy SHA256:            {taxonomy_sha}")
    print(f"Baseline runtime SHA256:    {runtime_sha}")
    print()
    print("Design:                     FACTORISED EVIDENCE ADJUDICATION")
    print("Evidence support states:    5")
    print("Authoritative-home states:  3")
    print("Public API shape changed:   NO")
    print("Retrieval changed:          NO")
    print("Runtime replacement:        NOT AUTHORISED")
    print()
    print("Hard-coded benchmark logic: PROHIBITED")
    print("Section-specific routing:   PROHIBITED")
    print("Topic-specific status map:  PROHIBITED")
    print("Runtime eval-data access:   PROHIBITED")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Design contract SHA256:     {sha256(OUTPUT_PATH)}")
    print()
    print("Runtime files modified:     NONE")
    print("Runtime/model calls:        NONE")
    print("Retrieval/reranker calls:   NONE")
    print("Database writes:            NONE")
    print()
    print("Candidate-v4 design contract freeze: PASS")


if __name__ == "__main__":
    main()
