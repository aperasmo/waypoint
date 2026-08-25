"""Score a blind Waypoint reranker stability artifact against gold labels.

This scorer never calls retrieval or the LLM. It evaluates the already-saved
stability artifact produced from the frozen candidate snapshot.

It reports:
- production Recall@1 from frozen candidate rank 1;
- Recall@1 for each reranker run;
- section-majority Recall@1;
- per-case correctness across runs;
- variable cases whose section choice changes.

Run from backend/:
    uv run python -m scripts.score_reranker_stability
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
GOLD_PATH = BACKEND_DIR / "tests" / "eval_questions_adjudicated_v2.json"
SNAPSHOT_PATH = BACKEND_DIR / "tests" / "rerank_candidates_blind_v2.json"
STABILITY_PATH = BACKEND_DIR / "tests" / "rerank_stability_blind_v2.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def make_case_id(question: str) -> str:
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    return f"q_{digest[:16]}"


def main() -> None:
    for path in (GOLD_PATH, SNAPSHOT_PATH, STABILITY_PATH):
        if not path.exists():
            raise SystemExit(f"Required file not found: {path}")

    gold = json.loads(GOLD_PATH.read_text(encoding="utf-8"))
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    stability = json.loads(STABILITY_PATH.read_text(encoding="utf-8"))

    if stability.get("candidate_snapshot_sha256") != sha256(SNAPSHOT_PATH):
        raise SystemExit(
            "Stability artifact was not produced from the current candidate "
            "snapshot."
        )

    gold_cases = gold.get("questions")
    snapshot_cases = snapshot.get("cases")
    stability_results = stability.get("results")

    if not isinstance(gold_cases, list):
        raise SystemExit("Gold file has no valid questions list.")
    if not isinstance(snapshot_cases, list):
        raise SystemExit("Snapshot has no valid cases list.")
    if not isinstance(stability_results, list):
        raise SystemExit("Stability artifact has no valid results list.")

    runs = stability.get("runs_per_case")
    if not isinstance(runs, int) or runs < 2:
        raise SystemExit("Invalid runs_per_case in stability artifact.")

    gold_by_id: dict[str, dict] = {}
    for case in gold_cases:
        question = case.get("question")
        expected = case.get("expected_sections")
        if not isinstance(question, str) or not question.strip():
            raise SystemExit("Gold case contains an invalid question.")
        if not isinstance(expected, list):
            raise SystemExit(
                f"Invalid expected_sections for gold question: {question!r}"
            )

        question = question.strip()
        case_id = make_case_id(question)
        if case_id in gold_by_id:
            raise SystemExit(f"Duplicate gold case_id: {case_id}")

        gold_by_id[case_id] = {
            "question": question,
            "expected_sections": expected,
        }

    snapshot_by_id: dict[str, dict] = {}
    for case in snapshot_cases:
        case_id = case.get("case_id")
        question = case.get("question")
        candidates = case.get("candidates")

        if not isinstance(case_id, str) or not case_id:
            raise SystemExit("Snapshot case has invalid case_id.")
        if not isinstance(question, str) or not question.strip():
            raise SystemExit(f"Snapshot case {case_id} has invalid question.")
        if not isinstance(candidates, list) or len(candidates) != 5:
            raise SystemExit(
                f"Snapshot case {case_id} must contain exactly 5 candidates."
            )
        if case_id in snapshot_by_id:
            raise SystemExit(f"Duplicate snapshot case_id: {case_id}")

        snapshot_by_id[case_id] = case

    stability_by_id: dict[str, dict] = {}
    for result in stability_results:
        case_id = result.get("case_id")
        question = result.get("question")
        chosen_sections = result.get("chosen_sections")
        chosen_indices = result.get("chosen_indices")

        if not isinstance(case_id, str) or not case_id:
            raise SystemExit("Stability result has invalid case_id.")
        if not isinstance(question, str) or not question.strip():
            raise SystemExit(
                f"Stability result {case_id} has invalid question."
            )
        if not isinstance(chosen_sections, list) or len(chosen_sections) != runs:
            raise SystemExit(
                f"Stability result {case_id} has invalid chosen_sections."
            )
        if not isinstance(chosen_indices, list) or len(chosen_indices) != runs:
            raise SystemExit(
                f"Stability result {case_id} has invalid chosen_indices."
            )
        if case_id in stability_by_id:
            raise SystemExit(f"Duplicate stability case_id: {case_id}")

        stability_by_id[case_id] = result

    ids = set(gold_by_id)
    if ids != set(snapshot_by_id) or ids != set(stability_by_id):
        raise SystemExit(
            "Gold, snapshot and stability artifacts do not contain the same "
            "case IDs."
        )

    production_hits = 0
    run_hits = [0 for _ in range(runs)]
    majority_hits = 0
    variable_section_cases: list[dict] = []
    per_case_rows: list[dict] = []

    for case_id in sorted(ids):
        gold_case = gold_by_id[case_id]
        snapshot_case = snapshot_by_id[case_id]
        stability_case = stability_by_id[case_id]

        question = gold_case["question"]
        if snapshot_case["question"].strip() != question:
            raise SystemExit(
                f"Question mismatch between gold and snapshot for {case_id}"
            )
        if stability_case["question"].strip() != question:
            raise SystemExit(
                f"Question mismatch between gold and stability for {case_id}"
            )

        expected = set(gold_case["expected_sections"])
        production_section = snapshot_case["candidates"][0]["section_code"]
        production_ok = production_section in expected
        production_hits += int(production_ok)

        chosen_sections = stability_case["chosen_sections"]

        correctness: list[bool] = []
        for run_index, section in enumerate(chosen_sections):
            ok = section in expected
            correctness.append(ok)
            run_hits[run_index] += int(ok)

        counts = Counter(chosen_sections)
        max_count = max(counts.values())
        majority_sections = sorted(
            section for section, count in counts.items() if count == max_count
        )

        # With an odd run count there should normally be one majority section.
        # Fail closed on an exact tie rather than silently inventing a rule.
        if len(majority_sections) != 1:
            raise SystemExit(
                f"No unique section majority for {case_id}: {dict(counts)}"
            )

        majority_section = majority_sections[0]
        majority_ok = majority_section in expected
        majority_hits += int(majority_ok)

        if len(counts) > 1:
            variable_section_cases.append(
                {
                    "case_id": case_id,
                    "question": question,
                    "expected": gold_case["expected_sections"],
                    "chosen_sections": chosen_sections,
                    "correctness": correctness,
                    "majority_section": majority_section,
                    "majority_ok": majority_ok,
                }
            )

        per_case_rows.append(
            {
                "case_id": case_id,
                "question": question,
                "expected": gold_case["expected_sections"],
                "production": production_section,
                "production_ok": production_ok,
                "chosen_sections": chosen_sections,
                "correctness": correctness,
                "majority_section": majority_section,
                "majority_ok": majority_ok,
            }
        )

    total = len(ids)

    print("Waypoint reranker stability scoring")
    print("=" * 35)
    print(f"Gold:       {GOLD_PATH}")
    print(f"Snapshot:   {SNAPSHOT_PATH}")
    print(f"Stability:  {STABILITY_PATH}")
    print()
    print("No retrieval calls:          PASS")
    print("No reranker calls:           PASS")
    print("Gold used only for scoring:  PASS")
    print()
    print("Recall@1")
    print("-" * 76)
    print(
        f"Production frozen top-1:    {production_hits}/{total} "
        f"({production_hits / total:.0%})"
    )

    for index, hits in enumerate(run_hits, start=1):
        print(
            f"Reranker run {index}:           {hits}/{total} "
            f"({hits / total:.0%})  "
            f"delta={hits - production_hits:+d}"
        )

    print(
        f"Section majority ({runs} runs): "
        f"{majority_hits}/{total} "
        f"({majority_hits / total:.0%})  "
        f"delta={majority_hits - production_hits:+d}"
    )

    print()
    print("Stability")
    print("-" * 76)
    print(
        f"Section-stable cases:       "
        f"{total - len(variable_section_cases)}/{total} "
        f"({(total - len(variable_section_cases)) / total:.0%})"
    )
    print(
        f"Section-variable cases:     {len(variable_section_cases)}"
    )

    if variable_section_cases:
        print()
        print("Section-variable cases")
        print("-" * 76)

        for row in variable_section_cases:
            marks = [
                f"{section}{'✓' if ok else '✗'}"
                for section, ok in zip(
                    row["chosen_sections"],
                    row["correctness"],
                    strict=True,
                )
            ]
            print(f"{row['case_id']}  {row['question']}")
            print(f"    wanted:   {', '.join(row['expected'])}")
            print(f"    runs:     {', '.join(marks)}")
            print(
                f"    majority: {row['majority_section']} "
                f"{'✓' if row['majority_ok'] else '✗'}"
            )

    print()
    print("Per-run range")
    print("-" * 76)
    print(
        f"Best reranker run:          {max(run_hits)}/{total} "
        f"({max(run_hits) / total:.0%})"
    )
    print(
        f"Worst reranker run:         {min(run_hits)}/{total} "
        f"({min(run_hits) / total:.0%})"
    )
    print(
        f"Run-to-run spread:          {max(run_hits) - min(run_hits)} question(s)"
    )

    print()
    print(f"Gold SHA256:      {sha256(GOLD_PATH)}")
    print(f"Snapshot SHA256:  {sha256(SNAPSHOT_PATH)}")
    print(f"Stability SHA256: {sha256(STABILITY_PATH)}")


if __name__ == "__main__":
    main()