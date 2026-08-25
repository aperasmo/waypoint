"""Freeze the answer-architecture engineering diagnosis after v4-v6.

This is a DEVELOPMENT DIAGNOSIS artifact only.

It does not:
- modify production runtime;
- authorise candidate v7;
- call any model;
- call retrieval, embeddings, or reranking;
- write to the database.

Run from backend/:
    uv run python -m py_compile scripts/freeze_answer_architecture_diagnosis.py
    uv run python -m scripts.freeze_answer_architecture_diagnosis
"""

from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

RUNTIME_PATH = BACKEND_DIR / "app" / "api" / "routes" / "ask.py"

AUDIT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_architecture_error_audit_v2_v5_v6_rev2.json"
)

V5_REJECTION_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_candidate_v5_rejection.json"
)

V6_REJECTION_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_candidate_v6_rejection.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_architecture_diagnosis_v1.json"
)

EXPECTED_RUNTIME_SHA256 = (
    "FF879300C09B195681E109E5B4F5D807"
    "C89216E986AE4AA9338B104FA99AAD0E"
)

EXPECTED_AUDIT_SHA256 = (
    "39D310220F70056822761D2E4BB66778"
    "FD00BA26F5210E13690F72FB287E600C"
)

EXPECTED_V5_REJECTION_SHA256 = (
    "BB1F372DD1533FEF5D08F27A9AF9B227"
    "AF7E5107D4071613902CA9D954163F8E"
)

EXPECTED_V6_REJECTION_SHA256 = (
    "534C15602F528CC766C8028734F38D4C"
    "15938CF0EC156B1F7AF9C6F70D606B74"
)

EXPECTED_V2_UNDERREACH_IDS = {
    "ext_85192ee7adceec0c",
    "ext2_d8797e336a9cc692",
    "ext2_8c067aa632151edd",
    "ext2_139daec2a4cbe690",
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
            f"Path:     {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Refusing to freeze the engineering diagnosis."
        )


def load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be a JSON object.")

    return payload


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Diagnosis artifact already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_sha(
        RUNTIME_PATH,
        EXPECTED_RUNTIME_SHA256,
        "Frozen production candidate-v2 runtime",
    )
    require_sha(
        AUDIT_PATH,
        EXPECTED_AUDIT_SHA256,
        "Revised structured error audit",
    )
    require_sha(
        V5_REJECTION_PATH,
        EXPECTED_V5_REJECTION_SHA256,
        "Candidate-v5 rejection",
    )
    require_sha(
        V6_REJECTION_PATH,
        EXPECTED_V6_REJECTION_SHA256,
        "Candidate-v6 rejection",
    )

    audit = load_json(AUDIT_PATH)
    v5_rejection = load_json(V5_REJECTION_PATH)
    v6_rejection = load_json(V6_REJECTION_PATH)

    if audit.get("schema") != (
        "waypoint-answer-architecture-error-audit-v2-v5-v6"
    ):
        raise RuntimeError("Unexpected revised audit schema.")

    if audit.get("status") != (
        "DEVELOPMENT_DIAGNOSTIC_ONLY_NO_V7_AUTHORITY"
    ):
        raise RuntimeError("Unexpected revised audit status.")

    if v5_rejection.get("decision", {}).get("candidate_v5") != "REJECT":
        raise RuntimeError("Candidate v5 is not frozen as rejected.")

    if v6_rejection.get("decision", {}).get("candidate_v6") != "REJECT":
        raise RuntimeError("Candidate v6 is not frozen as rejected.")

    summary = audit.get("summary", {})

    if summary.get("case_count") != 111:
        raise RuntimeError("Unexpected audit case count.")

    gold_counts = summary.get("gold_class_counts", {})
    if gold_counts != {
        "corpus_gap": 68,
        "external_source_required": 18,
        "sufficient": 25,
    }:
        raise RuntimeError("Unexpected gold class counts.")

    any_coverage = summary.get(
        "sufficient_evidence_availability_any_expected_section",
        {},
    )

    complete_coverage = summary.get(
        "sufficient_evidence_availability_all_listed_expected_sections",
        {},
    )

    if any_coverage.get("any_expected_section_present_top5") != 25:
        raise RuntimeError(
            "Expected all 25 sufficient cases to have at least one "
            "expected section in top-5."
        )

    if any_coverage.get("any_expected_section_present_top10_only", 0) != 0:
        raise RuntimeError("Unexpected any-section top-10-only count.")

    if any_coverage.get("no_expected_section_present_top10", 0) != 0:
        raise RuntimeError("Unexpected no-expected-section top-10 count.")

    if complete_coverage.get(
        "all_listed_expected_sections_present_top5"
    ) != 23:
        raise RuntimeError(
            "Unexpected complete expected-section top-5 count."
        )

    if complete_coverage.get(
        "all_listed_expected_sections_present_top10_only"
    ) != 1:
        raise RuntimeError(
            "Unexpected complete expected-section top-10-only count."
        )

    if complete_coverage.get(
        "some_but_not_all_listed_expected_sections_present_top5"
    ) != 1:
        raise RuntimeError(
            "Unexpected partial listed expected-section top-5 count."
        )

    if complete_coverage.get(
        "some_but_not_all_listed_expected_sections_present_top10_only",
        0,
    ) != 0:
        raise RuntimeError(
            "Unexpected partial listed expected-section top-10-only count."
        )

    if complete_coverage.get(
        "no_listed_expected_sections_present_top10",
        0,
    ) != 0:
        raise RuntimeError(
            "Unexpected no-listed-expected-section top-10 count."
        )

    mechanisms = summary.get(
        "frozen_v2_failure_mechanism_recovery",
        {},
    )

    expected_mechanisms = {
        "authoritative_home_resolution_failure": {
            "v2_failure_count": 13,
            "v5_fixed": 1,
            "v6_fixed": 3,
            "v5_still_wrong": 12,
            "v6_still_wrong": 10,
        },
        "scope_entailment_overreach": {
            "v2_failure_count": 11,
            "v5_fixed": 4,
            "v6_fixed": 9,
            "v5_still_wrong": 7,
            "v6_still_wrong": 2,
        },
        "scope_entailment_underreach": {
            "v2_failure_count": 4,
            "v5_fixed": 2,
            "v6_fixed": 0,
            "v5_still_wrong": 2,
            "v6_still_wrong": 4,
        },
    }

    if mechanisms != expected_mechanisms:
        raise RuntimeError("Frozen failure-mechanism recovery counts changed.")

    regressions = summary.get(
        "new_regressions_from_v2_correct",
        {},
    )

    if regressions.get("v5", {}).get("count") != 9:
        raise RuntimeError("Unexpected v5 regression count.")

    if regressions.get("v6", {}).get("count") != 16:
        raise RuntimeError("Unexpected v6 regression count.")

    underreach = summary.get(
        "sufficient_underreach_despite_expected_support_in_top5",
        {},
    )

    v2_underreach_ids = set(
        underreach.get("v2", {}).get("case_ids", [])
    )

    if v2_underreach_ids != EXPECTED_V2_UNDERREACH_IDS:
        raise RuntimeError("Unexpected frozen v2 underreach case IDs.")

    cases = {
        item["case_id"]: item
        for item in audit.get("cases", [])
        if isinstance(item, dict)
        and isinstance(item.get("case_id"), str)
    }

    if len(cases) != 111:
        raise RuntimeError("Unexpected detailed audit case count.")

    v2_underreach_complete_top5 = []
    v2_underreach_partial_top5 = []

    for case_id in sorted(EXPECTED_V2_UNDERREACH_IDS):
        item = cases[case_id]
        availability = item.get("evidence_availability", {})

        if availability.get(
            "all_listed_expected_sections_in_top5"
        ) is True:
            v2_underreach_complete_top5.append(case_id)
        else:
            v2_underreach_partial_top5.append(case_id)

    if len(v2_underreach_complete_top5) != 3:
        raise RuntimeError(
            "Expected exactly 3/4 frozen v2 underreach cases to have "
            "the complete listed expected-section set in top-5."
        )

    if len(v2_underreach_partial_top5) != 1:
        raise RuntimeError(
            "Expected exactly 1/4 frozen v2 underreach cases to have "
            "only partial listed expected-section coverage in top-5."
        )

    diagnosis = {
        "schema": "waypoint-answer-architecture-diagnosis-v1",
        "status": "FROZEN_DEVELOPMENT_DIAGNOSIS_NO_RUNTIME_CHANGE",
        "frozen_on": str(date.today()),
        "production_baseline": {
            "candidate": "evidence_adequacy_v2",
            "runtime_sha256": EXPECTED_RUNTIME_SHA256,
        },
        "source_artifacts": {
            "revised_error_audit_sha256": EXPECTED_AUDIT_SHA256,
            "candidate_v5_rejection_sha256": (
                EXPECTED_V5_REJECTION_SHA256
            ),
            "candidate_v6_rejection_sha256": (
                EXPECTED_V6_REJECTION_SHA256
            ),
        },
        "observations": {
            "retired_development_case_count": 111,
            "gold_class_counts": gold_counts,
            "sufficient_retrieval_coverage": {
                "at_least_one_expected_section_top5": {
                    "count": 25,
                    "total": 25,
                },
                "all_listed_expected_sections_top5": {
                    "count": 23,
                    "total": 25,
                },
                "all_listed_expected_sections_by_top10": {
                    "count": 24,
                    "total": 25,
                },
                "some_but_not_all_listed_expected_sections_by_top10": {
                    "count": 1,
                    "total": 25,
                },
                "no_listed_expected_sections_by_top10": {
                    "count": 0,
                    "total": 25,
                },
            },
            "frozen_v2_failures": {
                "total": 28,
                "authoritative_home_resolution_failure": 13,
                "scope_entailment_overreach": 11,
                "scope_entailment_underreach": 4,
            },
            "v2_underreach_retrieval_detail": {
                "complete_listed_expected_sections_in_top5": {
                    "count": len(v2_underreach_complete_top5),
                    "total": 4,
                    "case_ids": v2_underreach_complete_top5,
                },
                "partial_listed_expected_sections_in_top5": {
                    "count": len(v2_underreach_partial_top5),
                    "total": 4,
                    "case_ids": v2_underreach_partial_top5,
                },
            },
            "candidate_v5": {
                "combined_accuracy": 81 / 111,
                "v2_correct_baseline": 83 / 111,
                "new_regressions_from_v2_correct": 9,
                "authoritative_home_failures_fixed": 1,
                "scope_overreach_failures_fixed": 4,
                "scope_underreach_failures_fixed": 2,
            },
            "candidate_v6": {
                "combined_accuracy": 79 / 111,
                "v2_correct_baseline": 83 / 111,
                "new_regressions_from_v2_correct": 16,
                "authoritative_home_failures_fixed": 3,
                "scope_overreach_failures_fixed": 9,
                "scope_underreach_failures_fixed": 0,
                "external_source_required_correct": {
                    "count": 6,
                    "total": 18,
                    "same_as_candidate_v2": True,
                },
            },
        },
        "engineering_diagnosis": {
            "retrieval": {
                "classification": (
                    "NOT_PRIMARY_OBSERVED_BOTTLENECK_ON_RETIRED_"
                    "SUFFICIENT_CASES"
                ),
                "scope": (
                    "This conclusion is limited to the retired external-v1/v2 "
                    "development cases. It does not establish that retrieval "
                    "is globally optimal."
                ),
                "basis": (
                    "All 25 gold-sufficient cases had at least one expected "
                    "section in retrieval top-5, 23/25 had the complete listed "
                    "expected-section set in top-5, and 24/25 had the complete "
                    "listed set by top-10. Three of the four frozen v2 "
                    "scope-underreach failures had their complete listed "
                    "expected-section set already in top-5."
                ),
            },
            "evidence_classification": {
                "classification": "PRIMARY_OBSERVED_FAILURE_AREA",
                "basis": (
                    "The dominant development failures concern deciding "
                    "whether retrieved evidence entails the exact proposition "
                    "without either overreaching or underreaching."
                ),
            },
            "authoritative_home_resolution": {
                "classification": "UNRESOLVED_PRIMARY_FAILURE_AREA",
                "basis": (
                    "13/28 frozen v2 failures concern authoritative-home "
                    "resolution. V5 fixed 1/13 and v6 fixed 3/13. V6's "
                    "combined external-source-required performance remained "
                    "6/18, the same as candidate v2."
                ),
            },
            "prompt_only_decomposition": {
                "classification": "NOT_SUPPORTED_FOR_NEXT_CANDIDATE",
                "basis": (
                    "V5 and v6 moved the precision/recall boundary but both "
                    "underperformed candidate v2 overall. V6 strongly reduced "
                    "scope overreach while creating 13 new sufficient-case "
                    "regressions and fixing none of the four frozen "
                    "underreach failures."
                ),
            },
        },
        "decisions": {
            "production_candidate": "evidence_adequacy_v2",
            "production_runtime_change_authorised": False,
            "retrieval_change_authorised_from_this_audit": False,
            "prompt_only_candidate_v7_authorised": False,
            "candidate_v7_build_authorised": False,
            "fresh_external_v3_holdout_authorised": False,
        },
        "next_engineering_task": {
            "name": "independent_authoritative_source_boundary_specification",
            "authorised": True,
            "runtime_implementation_authorised": False,
            "purpose": (
                "Define, from independent product/source architecture rather "
                "than benchmark case mappings, which kinds of information "
                "are authoritative Operational Manual content versus which "
                "kinds are maintained by bounded external official sources."
            ),
            "constraints": [
                (
                    "The specification must be generic and source-oriented, "
                    "not a lookup table of benchmark questions, visa "
                    "categories, section codes, or expected answers."
                ),
                (
                    "It must not import case IDs, gold statuses, expected "
                    "sections, or adjudication notes into runtime design."
                ),
                (
                    "It should be grounded independently in the actual "
                    "authoritative-source architecture before any candidate "
                    "implementation is designed."
                ),
                (
                    "Candidate v7 remains unauthorised until that source "
                    "boundary specification is reviewed and frozen."
                ),
            ],
        },
        "interpretation_constraints": [
            (
                "Retired external v1/v2 are development diagnostics only and "
                "cannot support a fresh-generalisation claim."
            ),
            (
                "The listed expected sections in gold are evaluation evidence "
                "references; the audit does not assert that every listed "
                "section is independently necessary in every case."
            ),
            (
                "No conclusion here authorises widening production to "
                "unrestricted web search."
            ),
        ],
    }

    OUTPUT_PATH.write_text(
        json.dumps(diagnosis, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    saved = load_json(OUTPUT_PATH)

    if saved.get("decisions", {}).get(
        "candidate_v7_build_authorised"
    ) is not False:
        raise RuntimeError(
            "Diagnosis unexpectedly authorises candidate v7."
        )

    if saved.get("next_engineering_task", {}).get(
        "runtime_implementation_authorised"
    ) is not False:
        raise RuntimeError(
            "Diagnosis unexpectedly authorises runtime implementation."
        )

    print("Waypoint answer-architecture engineering diagnosis freeze")
    print("=" * 58)
    print(f"Production v2 SHA256:      {sha256(RUNTIME_PATH)}")
    print(f"Revised audit SHA256:      {sha256(AUDIT_PATH)}")
    print(f"V5 rejection SHA256:       {sha256(V5_REJECTION_PATH)}")
    print(f"V6 rejection SHA256:       {sha256(V6_REJECTION_PATH)}")
    print()
    print("Retired development cases: 111")
    print("Frozen v2 failures:        28")
    print()
    print("Sufficient retrieval coverage")
    print("-" * 58)
    print("At least one expected section top-5: 25/25")
    print("All listed expected sections top-5:  23/25")
    print("All listed expected sections top-10: 24/25")
    print("No listed expected section top-10:    0/25")
    print()
    print("Frozen v2 underreach")
    print("-" * 58)
    print(
        "Complete listed expected set already top-5: "
        f"{len(v2_underreach_complete_top5)}/4"
    )
    print(
        "Only partial listed expected set in top-5:  "
        f"{len(v2_underreach_partial_top5)}/4"
    )
    print()
    print("Failure mechanisms")
    print("-" * 58)
    print("Authoritative-home resolution: 13")
    print("Scope entailment overreach:    11")
    print("Scope entailment underreach:    4")
    print()
    print("Diagnosis")
    print("-" * 58)
    print("Retrieval:                   NOT PRIMARY OBSERVED BOTTLENECK")
    print("Evidence classification:     PRIMARY OBSERVED FAILURE AREA")
    print("Authoritative-home resolution:UNRESOLVED PRIMARY FAILURE AREA")
    print("Prompt-only decomposition:   DO NOT CONTINUE")
    print()
    print("Production remains:          CANDIDATE V2")
    print("Candidate v7 build:          NOT AUTHORISED")
    print("Fresh external-v3 holdout:   NOT AUTHORISED")
    print()
    print(
        "Next task:                  INDEPENDENT AUTHORITATIVE-SOURCE "
        "BOUNDARY SPECIFICATION"
    )
    print("Runtime implementation:      NOT AUTHORISED")
    print()
    print(f"Output:                       {OUTPUT_PATH}")
    print(f"Diagnosis SHA256:             {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                  NONE")
    print("Retrieval/reranker calls:     NONE")
    print("Database writes:              NONE")
    print("Runtime files modified:       NONE")
    print()
    print("Engineering diagnosis freeze: PASS")


if __name__ == "__main__":
    main()
