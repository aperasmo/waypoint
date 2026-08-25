"""Build a structured answer-architecture error audit for v2, v5, and v6.

DEVELOPMENT / DIAGNOSTIC ONLY.

Purpose
-------
Determine what the rejected v5/v6 experiments actually changed before any
candidate-v7 design is authorised.

The audit combines:
- frozen external-v1/v2 gold;
- frozen external-v1/v2 adjudication retrieval packets;
- frozen production candidate-v2 predictions;
- rejected candidate-v5 predictions;
- rejected candidate-v6 predictions, including explicit contract errors;
- the frozen candidate-v2 human-reviewed failure taxonomy.

It answers factual questions such as:
- Was the expected supporting section already present in retrieval top-5?
- Which frozen v2 failure mechanisms did v5 or v6 recover?
- What new regressions did v5/v6 create on cases v2 had correct?
- Did external-authority classification improve net of regressions?
- Did v5/v6 reject sufficient cases even when gold support was already in
  retrieval top-5?

It deliberately does NOT:
- call any model;
- call retrieval, embeddings, or reranking;
- modify runtime code;
- write to the database;
- assign new semantic failure mechanisms to v5/v6-only regressions;
- authorise candidate v7.

Run from backend/:
    uv run python -m py_compile scripts/build_answer_architecture_error_audit.py
    uv run python -m scripts.build_answer_architecture_error_audit

Output:
    tests/answer_architecture_error_audit_v2_v5_v6.json
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

V1_GOLD_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_gold_v1.json"
)
V2_GOLD_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_gold_v2.json"
)

V1_PACKET_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_packet_v1.json"
)
V2_PACKET_PATH = (
    BACKEND_DIR / "tests" / "external_adjudication_packet_v2.json"
)

V1_V2_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_evidence_adequacy_v2.json"
)
V2_V2_PATH = (
    BACKEND_DIR / "tests" / "external_predictions_blind_v2.json"
)

V1_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v5.json"
)
V2_V5_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v2_candidate_v5.json"
)

V1_V6_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v1_candidate_v6.json"
)
V2_V6_PATH = (
    BACKEND_DIR
    / "tests"
    / "external_predictions_dev_v2_candidate_v6.json"
)

TAXONOMY_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_failure_taxonomy_candidate_v2_frozen.json"
)

OUTPUT_PATH = (
    BACKEND_DIR
    / "tests"
    / "answer_architecture_error_audit_v2_v5_v6.json"
)

EXPECTED = {
    V1_GOLD_PATH: (
        "11D21AF433C30F99665915F0536FFE30"
        "B4AE1E76972DB6F036BED38B2D5ECCB3"
    ),
    V2_GOLD_PATH: (
        "D584326117A4CEF64C869225AD9186FF"
        "95C1D0753ED93706A0748C6ABCC4FA36"
    ),
    V1_PACKET_PATH: (
        "3C5E5FC0F083DD2642EE22720E1F7256"
        "9896EED104FF332639244BEC334ABA4F"
    ),
    V2_PACKET_PATH: (
        "2D4F12A75ECAA30378CD6E601814653C"
        "3CD42F6C893E486D1F59362DB8646F2A"
    ),
    V1_V2_PATH: (
        "0F1E84F74DC1B50C6217A1909A48A5F"
        "F922FA537029737E1E8CE3769488FD541"
    ),
    V2_V2_PATH: (
        "BCC045922577E84AA89CBBE19587E56C"
        "634ABEB119F9476191B050FB2459493D"
    ),
    V1_V5_PATH: (
        "BFB75B7AB9AE9385AAC88C6956407807"
        "678229FDD04E5F0D4A1B7AAAE9569DAB"
    ),
    V2_V5_PATH: (
        "70906FB9E78FA45F983EEADC9375AC1F"
        "82FC092716B05B564A109E96E6D1899D"
    ),
    V1_V6_PATH: (
        "24BDDB4B0AA69BBE93552F075E3A801C"
        "8905422B4F5EBBD01375779640A295FF"
    ),
    V2_V6_PATH: (
        "2150DA5E6E093AA1FBF8ECA39362306B"
        "50115598561BAC15D02C8573D61C3A45"
    ),
    TAXONOMY_PATH: (
        "0AB84EB3A83F6B97A2CBBA603C6D5304"
        "19E93A07DC6E8671183462E17DA5BCB9"
    ),
}

STATUSES = (
    "sufficient",
    "corpus_gap",
    "external_source_required",
)
ERROR_STATUS = "candidate_error"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def load_json(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(payload, dict):
        raise RuntimeError(f"{path.name}: root must be an object.")

    return payload


def require_all_hashes() -> None:
    for path, expected in EXPECTED.items():
        actual = sha256(path)
        if actual != expected:
            raise SystemExit(
                f"SHA mismatch: {path}\n"
                f"Expected: {expected}\n"
                f"Actual:   {actual}\n"
                "Refusing to build audit from changed artifacts."
            )


def gold_map(payload: dict, expected_schema: str) -> dict[str, dict]:
    if payload.get("schema") != expected_schema:
        raise RuntimeError(
            f"Unexpected gold schema: {payload.get('schema')!r}"
        )

    if payload.get("status") != "FROZEN_DO_NOT_TUNE_ON_THIS_SET":
        raise RuntimeError("Gold status changed.")

    result: dict[str, dict] = {}

    for item in payload.get("questions", []):
        if item.get("benchmark_status") != "include":
            continue

        case_id = item.get("candidate_id")
        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Gold item has invalid candidate_id.")

        if case_id in result:
            raise RuntimeError(f"Duplicate gold case: {case_id}")

        status = item.get("evidence_status")
        if status not in STATUSES:
            raise RuntimeError(
                f"{case_id}: invalid gold evidence_status."
            )

        result[case_id] = item

    return result


def packet_map(payload: dict, expected_schema: str) -> dict[str, dict]:
    if payload.get("schema") != expected_schema:
        raise RuntimeError(
            f"Unexpected packet schema: {payload.get('schema')!r}"
        )

    if payload.get("retriever_top_k") != 10:
        raise RuntimeError("Expected adjudication packet retrieval top-k 10.")

    result: dict[str, dict] = {}

    for item in payload.get("questions", []):
        case_id = item.get("candidate_id")
        candidates = item.get("retrieval_candidates")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Packet item has invalid candidate_id.")

        if not isinstance(candidates, list):
            raise RuntimeError(
                f"{case_id}: retrieval_candidates must be a list."
            )

        if case_id in result:
            raise RuntimeError(f"Duplicate packet case: {case_id}")

        result[case_id] = item

    return result


def prediction_map(
    payload: dict,
    *,
    expected_schema: str,
    candidate: str,
) -> dict[str, dict]:
    if payload.get("schema") != expected_schema:
        raise RuntimeError(
            f"{candidate}: unexpected schema {payload.get('schema')!r}."
        )

    result: dict[str, dict] = {}

    for item in payload.get("predictions", []):
        case_id = item.get("case_id")
        status = item.get("evidence_status")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError(
                f"{candidate}: prediction has invalid case_id."
            )

        if status not in STATUSES:
            raise RuntimeError(
                f"{candidate}/{case_id}: invalid evidence_status."
            )

        if case_id in result:
            raise RuntimeError(
                f"{candidate}: duplicate case_id {case_id}."
            )

        result[case_id] = item

    if candidate == "v6":
        if payload.get("candidate_errors_are_scoring_failures") is not True:
            raise RuntimeError("v6 error-scoring contract changed.")

        for item in payload.get("errors", []):
            case_id = item.get("case_id")

            if not isinstance(case_id, str) or not case_id:
                raise RuntimeError("v6 error has invalid case_id.")

            if case_id in result:
                raise RuntimeError(
                    f"v6 duplicate prediction/error case: {case_id}"
                )

            if item.get("error_type") != "candidate_contract_error":
                raise RuntimeError(
                    f"v6/{case_id}: unexpected error type."
                )

            result[case_id] = {
                "case_id": case_id,
                "question": item.get("question"),
                "evidence_status": ERROR_STATUS,
                "citations": [],
                "candidate_error": {
                    "status_code": item.get("status_code"),
                    "detail": item.get("detail"),
                },
            }

    return result


def taxonomy_map(payload: dict) -> dict[str, dict]:
    if payload.get("schema") != (
        "waypoint-answer-failure-taxonomy-candidate-v2-frozen"
    ):
        raise RuntimeError("Unexpected frozen taxonomy schema.")

    if payload.get("status") != (
        "FROZEN_DEVELOPMENT_DESIGN_BASIS_DO_NOT_USE_AS_RUNTIME"
    ):
        raise RuntimeError("Frozen taxonomy status changed.")

    result: dict[str, dict] = {}

    for item in payload.get("items", []):
        case_id = item.get("case_id")

        if not isinstance(case_id, str) or not case_id:
            raise RuntimeError("Taxonomy item has invalid case_id.")

        if case_id in result:
            raise RuntimeError(
                f"Duplicate taxonomy case_id: {case_id}"
            )

        result[case_id] = item

    if len(result) != 28:
        raise RuntimeError(
            f"Expected 28 frozen v2 taxonomy items, got {len(result)}."
        )

    return result


def retrieval_codes(packet_item: dict, limit: int) -> list[str]:
    candidates = sorted(
        packet_item["retrieval_candidates"],
        key=lambda item: item.get("rank", 999999),
    )

    return [
        item["section_code"]
        for item in candidates[:limit]
        if isinstance(item.get("section_code"), str)
    ]


def evidence_availability(
    gold_item: dict,
    packet_item: dict,
) -> dict:
    expected = set(gold_item.get("expected_sections", []))
    partial = set(gold_item.get("partial_support_sections", []))

    top5 = retrieval_codes(packet_item, 5)
    top10 = retrieval_codes(packet_item, 10)

    expected_top5 = sorted(expected & set(top5))
    expected_top10 = sorted(expected & set(top10))
    partial_top5 = sorted(partial & set(top5))
    partial_top10 = sorted(partial & set(top10))

    if gold_item["evidence_status"] == "sufficient":
        if not expected:
            raise RuntimeError(
                f"{gold_item['candidate_id']}: sufficient gold has "
                "no expected_sections."
            )

        if expected_top5:
            support_availability = "expected_support_present_top5"
        elif expected_top10:
            support_availability = "expected_support_present_top10_only"
        else:
            support_availability = "expected_support_absent_top10"
    else:
        support_availability = "not_applicable_non_sufficient_gold"

    return {
        "support_availability": support_availability,
        "retrieval_top5_sections": top5,
        "retrieval_top10_sections": top10,
        "expected_sections": sorted(expected),
        "expected_sections_in_top5": expected_top5,
        "expected_sections_in_top10": expected_top10,
        "partial_support_sections": sorted(partial),
        "partial_support_in_top5": partial_top5,
        "partial_support_in_top10": partial_top10,
    }


def candidate_snapshot(
    prediction: dict,
    gold_status: str,
) -> dict:
    status = prediction["evidence_status"]
    return {
        "evidence_status": status,
        "correct": status == gold_status,
        "candidate_error": status == ERROR_STATUS,
        "cited_sections": [
            citation["section_code"]
            for citation in prediction.get("citations", [])
            if isinstance(citation, dict)
            and isinstance(citation.get("section_code"), str)
        ],
    }


def main() -> None:
    if OUTPUT_PATH.exists():
        raise SystemExit(
            f"Audit already exists: {OUTPUT_PATH}\n"
            "Refusing to overwrite it."
        )

    require_all_hashes()

    v1_gold = gold_map(
        load_json(V1_GOLD_PATH),
        "waypoint-external-adjudication-gold-v1",
    )
    v2_gold = gold_map(
        load_json(V2_GOLD_PATH),
        "waypoint-external-adjudication-gold-v2",
    )

    if len(v1_gold) != 51 or len(v2_gold) != 60:
        raise RuntimeError(
            "Unexpected included gold case counts."
        )

    gold = {**v1_gold, **v2_gold}
    if len(gold) != 111:
        raise RuntimeError("Gold case IDs overlap.")

    v1_packet = packet_map(
        load_json(V1_PACKET_PATH),
        "waypoint-external-adjudication-packet-v1",
    )
    v2_packet = packet_map(
        load_json(V2_PACKET_PATH),
        "waypoint-external-adjudication-packet-v2",
    )
    packet = {**v1_packet, **v2_packet}

    v2_pred = {
        **prediction_map(
            load_json(V1_V2_PATH),
            expected_schema=(
                "waypoint-external-predictions-dev-v1-v2"
            ),
            candidate="v2",
        ),
        **prediction_map(
            load_json(V2_V2_PATH),
            expected_schema=(
                "waypoint-external-predictions-blind-v2"
            ),
            candidate="v2",
        ),
    }

    v5_pred = {
        **prediction_map(
            load_json(V1_V5_PATH),
            expected_schema=(
                "waypoint-external-predictions-dev-v1-candidate-v5"
            ),
            candidate="v5",
        ),
        **prediction_map(
            load_json(V2_V5_PATH),
            expected_schema=(
                "waypoint-external-predictions-dev-v2-candidate-v5"
            ),
            candidate="v5",
        ),
    }

    v6_pred = {
        **prediction_map(
            load_json(V1_V6_PATH),
            expected_schema=(
                "waypoint-external-predictions-dev-v1-candidate-v6"
            ),
            candidate="v6",
        ),
        **prediction_map(
            load_json(V2_V6_PATH),
            expected_schema=(
                "waypoint-external-predictions-dev-v2-candidate-v6"
            ),
            candidate="v6",
        ),
    }

    frozen_taxonomy = taxonomy_map(load_json(TAXONOMY_PATH))

    for label, mapping in (
        ("packet", packet),
        ("v2 predictions", v2_pred),
        ("v5 predictions", v5_pred),
        ("v6 predictions", v6_pred),
    ):
        missing = set(gold) - set(mapping)
        if missing:
            raise RuntimeError(
                f"{label} missing gold cases: {sorted(missing)}"
            )

    cases: list[dict] = []

    v2_failure_recovery: dict[str, Counter] = defaultdict(Counter)
    v2_failure_secondary: dict[str, Counter] = defaultdict(Counter)

    new_regressions = {
        "v5": [],
        "v6": [],
    }

    sufficient_availability = Counter()
    sufficient_underreach_despite_top5 = {
        "v2": [],
        "v5": [],
        "v6": [],
    }

    external_gold_trajectories = Counter()

    for case_id, gold_item in gold.items():
        dataset = (
            "external_v1"
            if case_id in v1_gold
            else "external_v2"
        )

        availability = evidence_availability(
            gold_item,
            packet[case_id],
        )

        snapshots = {
            "v2": candidate_snapshot(
                v2_pred[case_id],
                gold_item["evidence_status"],
            ),
            "v5": candidate_snapshot(
                v5_pred[case_id],
                gold_item["evidence_status"],
            ),
            "v6": candidate_snapshot(
                v6_pred[case_id],
                gold_item["evidence_status"],
            ),
        }

        if gold_item["evidence_status"] == "sufficient":
            sufficient_availability[
                availability["support_availability"]
            ] += 1

            if availability["support_availability"] == (
                "expected_support_present_top5"
            ):
                for candidate in ("v2", "v5", "v6"):
                    if snapshots[candidate]["evidence_status"] != (
                        "sufficient"
                    ):
                        sufficient_underreach_despite_top5[
                            candidate
                        ].append(case_id)

        if gold_item["evidence_status"] == "external_source_required":
            external_gold_trajectories[
                (
                    snapshots["v2"]["evidence_status"],
                    snapshots["v5"]["evidence_status"],
                    snapshots["v6"]["evidence_status"],
                )
            ] += 1

        v2_taxonomy_item = frozen_taxonomy.get(case_id)

        if v2_taxonomy_item:
            mechanism = v2_taxonomy_item["primary_mechanism"]
            secondary = v2_taxonomy_item["secondary_mechanism"]

            v2_failure_recovery[mechanism]["v2_failure_count"] += 1
            v2_failure_recovery[mechanism]["v5_fixed"] += int(
                snapshots["v5"]["correct"]
            )
            v2_failure_recovery[mechanism]["v6_fixed"] += int(
                snapshots["v6"]["correct"]
            )
            v2_failure_recovery[mechanism][
                "v5_still_wrong"
            ] += int(not snapshots["v5"]["correct"])
            v2_failure_recovery[mechanism][
                "v6_still_wrong"
            ] += int(not snapshots["v6"]["correct"])

            v2_failure_secondary[secondary]["count"] += 1
            v2_failure_secondary[secondary]["v5_fixed"] += int(
                snapshots["v5"]["correct"]
            )
            v2_failure_secondary[secondary]["v6_fixed"] += int(
                snapshots["v6"]["correct"]
            )

        if snapshots["v2"]["correct"]:
            for candidate in ("v5", "v6"):
                if not snapshots[candidate]["correct"]:
                    new_regressions[candidate].append(
                        {
                            "dataset": dataset,
                            "case_id": case_id,
                            "question": gold_item["question"],
                            "gold_evidence_status": (
                                gold_item["evidence_status"]
                            ),
                            "v2_evidence_status": (
                                snapshots["v2"]["evidence_status"]
                            ),
                            f"{candidate}_evidence_status": (
                                snapshots[candidate]["evidence_status"]
                            ),
                            "support_availability": availability[
                                "support_availability"
                            ],
                            "expected_sections_in_top5": availability[
                                "expected_sections_in_top5"
                            ],
                            "expected_sections": availability[
                                "expected_sections"
                            ],
                            "new_semantic_taxonomy": (
                                "UNASSIGNED_HUMAN_REVIEW_REQUIRED"
                            ),
                        }
                    )

        cases.append(
            {
                "dataset": dataset,
                "case_id": case_id,
                "question": gold_item["question"],
                "gold_evidence_status": gold_item["evidence_status"],
                "evidence_availability": availability,
                "candidate_results": snapshots,
                "frozen_v2_failure_taxonomy": (
                    {
                        "primary_mechanism": (
                            v2_taxonomy_item["primary_mechanism"]
                        ),
                        "secondary_mechanism": (
                            v2_taxonomy_item["secondary_mechanism"]
                        ),
                        "diagnostic_flags": list(
                            v2_taxonomy_item.get(
                                "diagnostic_flags",
                                [],
                            )
                        ),
                    }
                    if v2_taxonomy_item
                    else None
                ),
            }
        )

    v2_correct_count = sum(
        item["candidate_results"]["v2"]["correct"]
        for item in cases
    )

    if v2_correct_count != 83:
        raise RuntimeError(
            f"Expected 83 v2-correct cases, got {v2_correct_count}."
        )

    if len(frozen_taxonomy) != 28:
        raise RuntimeError("Frozen v2 failure count changed.")

    if len(new_regressions["v5"]) != 9:
        raise RuntimeError(
            f"Expected 9 v5 regressions from v2-correct cases, "
            f"got {len(new_regressions['v5'])}."
        )

    if len(new_regressions["v6"]) != 16:
        raise RuntimeError(
            f"Expected 16 v6 regressions from v2-correct cases, "
            f"got {len(new_regressions['v6'])}."
        )

    if sum(sufficient_availability.values()) != 25:
        raise RuntimeError("Expected 25 sufficient gold cases.")

    regression_class_counts = {
        candidate: dict(
            Counter(
                item["gold_evidence_status"]
                for item in rows
            )
        )
        for candidate, rows in new_regressions.items()
    }

    summary = {
        "case_count": 111,
        "gold_class_counts": dict(
            Counter(
                item["gold_evidence_status"]
                for item in cases
            )
        ),
        "sufficient_evidence_availability": dict(
            sufficient_availability
        ),
        "sufficient_underreach_despite_expected_support_in_top5": {
            candidate: {
                "count": len(case_ids),
                "case_ids": case_ids,
            }
            for candidate, case_ids
            in sufficient_underreach_despite_top5.items()
        },
        "frozen_v2_failure_mechanism_recovery": {
            mechanism: dict(counts)
            for mechanism, counts
            in sorted(v2_failure_recovery.items())
        },
        "frozen_v2_secondary_mechanism_recovery": {
            mechanism: dict(counts)
            for mechanism, counts
            in sorted(v2_failure_secondary.items())
        },
        "new_regressions_from_v2_correct": {
            "v5": {
                "count": len(new_regressions["v5"]),
                "by_gold_class": regression_class_counts["v5"],
            },
            "v6": {
                "count": len(new_regressions["v6"]),
                "by_gold_class": regression_class_counts["v6"],
            },
        },
        "external_gold_status_trajectories": [
            {
                "v2": trajectory[0],
                "v5": trajectory[1],
                "v6": trajectory[2],
                "count": count,
            }
            for trajectory, count
            in sorted(
                external_gold_trajectories.items(),
                key=lambda item: (
                    item[0][0],
                    item[0][1],
                    item[0][2],
                ),
            )
        ],
    }

    findings = {
        "retrieval_support_check": {
            "definition": (
                "For gold-sufficient cases only, compare frozen "
                "expected_sections against the pre-existing adjudication "
                "packet retrieval top-5/top-10. This is a factual retrieval "
                "availability diagnostic, not a new gold label."
            ),
            "expected_support_present_top5": (
                sufficient_availability[
                    "expected_support_present_top5"
                ]
            ),
            "expected_support_present_top10_only": (
                sufficient_availability[
                    "expected_support_present_top10_only"
                ]
            ),
            "expected_support_absent_top10": (
                sufficient_availability[
                    "expected_support_absent_top10"
                ]
            ),
        },
        "interpretation_guardrails": [
            (
                "A sufficient case whose expected section is already in "
                "retrieval top-5 but is predicted corpus_gap indicates "
                "answer-layer/evidence-adjudication underreach for that "
                "historical case, not a missing top-5 retrieval result."
            ),
            (
                "This audit cannot by itself prove that retrieval is globally "
                "optimal; it only measures expected-section availability for "
                "these retired adjudicated cases."
            ),
            (
                "New v5/v6 regressions do not receive an automatically "
                "invented semantic failure taxonomy."
            ),
            (
                "The frozen v2 taxonomy is reused only for the same 28 "
                "already-reviewed v2 failures."
            ),
            (
                "No candidate-v7 mechanism is authorised by this audit "
                "artifact."
            ),
        ],
    }

    output = {
        "schema": "waypoint-answer-architecture-error-audit-v2-v5-v6",
        "status": "DEVELOPMENT_DIAGNOSTIC_ONLY_NO_V7_AUTHORITY",
        "source_artifact_sha256": {
            path.name: expected
            for path, expected in EXPECTED.items()
        },
        "summary": summary,
        "findings": findings,
        "new_regressions": new_regressions,
        "cases": cases,
        "next_step": {
            "candidate_v7_build_authorised": False,
            "required_action": (
                "Review this factual audit and decide whether a generic "
                "intervention is justified before freezing any v7 design."
            ),
        },
    }

    OUTPUT_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    verify = load_json(OUTPUT_PATH)

    if verify.get("summary", {}).get("case_count") != 111:
        raise RuntimeError("Saved audit case_count verification failed.")

    if verify.get("next_step", {}).get(
        "candidate_v7_build_authorised"
    ) is not False:
        raise RuntimeError(
            "Audit unexpectedly authorises candidate v7."
        )

    mechanism_summary = verify["summary"][
        "frozen_v2_failure_mechanism_recovery"
    ]

    print("Waypoint answer-architecture structured error audit")
    print("=" * 53)
    print("Datasets:                   RETIRED EXTERNAL V1 + V2")
    print("Cases:                      111")
    print("Frozen v2 failures:         28")
    print("Candidate-v7 build:         NOT AUTHORISED")
    print()
    print("Sufficient-case retrieval availability")
    print("-" * 68)
    print(
        "Expected support in top-5: "
        f"{sufficient_availability['expected_support_present_top5']}/25"
    )
    print(
        "Expected support in top-10 only: "
        f"{sufficient_availability['expected_support_present_top10_only']}/25"
    )
    print(
        "Expected support absent top-10: "
        f"{sufficient_availability['expected_support_absent_top10']}/25"
    )
    print()
    print("Sufficient underreach despite expected support already in top-5")
    print("-" * 68)
    for candidate in ("v2", "v5", "v6"):
        count = len(
            sufficient_underreach_despite_top5[candidate]
        )
        print(f"{candidate:<4} {count:>2}/25")
    print()
    print("Recovery of frozen v2 failure mechanisms")
    print("-" * 68)
    for mechanism, counts in sorted(mechanism_summary.items()):
        print(
            f"{mechanism}\n"
            f"  v2 failures: {counts['v2_failure_count']}"
            f" | v5 fixed: {counts['v5_fixed']}"
            f" | v6 fixed: {counts['v6_fixed']}"
        )
    print()
    print("New regressions from cases frozen v2 had correct")
    print("-" * 68)
    for candidate in ("v5", "v6"):
        print(
            f"{candidate}: {len(new_regressions[candidate])} "
            f"{regression_class_counts[candidate]}"
        )
    print()
    print("External-source-required gold")
    print("-" * 68)
    for candidate, predictions in (
        ("v2", v2_pred),
        ("v5", v5_pred),
        ("v6", v6_pred),
    ):
        ext = [
            case_id
            for case_id, item in gold.items()
            if item["evidence_status"]
            == "external_source_required"
        ]
        correct = sum(
            predictions[case_id]["evidence_status"]
            == "external_source_required"
            for case_id in ext
        )
        print(f"{candidate}: {correct}/18 correct")
    print()
    print(f"Output:                     {OUTPUT_PATH}")
    print(f"Audit SHA256:               {sha256(OUTPUT_PATH)}")
    print()
    print("Model calls:                NONE")
    print("Retrieval calls:            NONE")
    print("Reranker calls:             NONE")
    print("Database writes:            NONE")
    print("Runtime modifications:      NONE")
    print("New semantic taxonomy:      NONE")
    print()
    print("Structured error audit: PASS")


if __name__ == "__main__":
    main()
