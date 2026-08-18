"""Evaluate Waypoint /ask on the two-axis answer contract.

Scores:
- evidence-status accuracy
- decision-boundary accuracy
- derived legacy outcome accuracy
- expected-section citation coverage
- repeated-run classification stability

The script still writes tests/answer_review.md for manual grounding and
no-personal-advice review. Those safety checks are intentionally not reduced
to an automated score.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

QUESTIONS_PATH = Path(__file__).parent.parent / "tests" / "eval_questions.json"
OUTPUT_PATH = Path(__file__).parent.parent / "tests" / "answer_review.md"
API_URL = "http://localhost:8100/ask"


def derive_outcome(evidence_status: str, decision_boundary: str) -> str:
    if evidence_status == "corpus_gap":
        return "type_a"
    if evidence_status == "external_source_required":
        return "type_b"
    if decision_boundary != "general_information":
        return "type_c"
    return "answered"


async def request_case(
    client: httpx.AsyncClient,
    question: str,
) -> dict[str, Any]:
    response = await client.post(API_URL, json={"question": question})
    response.raise_for_status()
    return response.json()


async def main(runs: int) -> None:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    cases = payload["questions"]

    total_calls = len(cases) * runs
    evidence_matches = 0
    boundary_matches = 0
    outcome_matches = 0
    citation_matches = 0
    successful_calls = 0

    rows: list[dict[str, Any]] = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for i, case in enumerate(cases, start=1):
            question = case["question"]
            print(f"  [{i}/{len(cases)}] {question[:60]}")

            expected_evidence = case["expected_evidence_status"]
            expected_boundary = case["expected_decision_boundary"]
            expected_outcome = derive_outcome(
                expected_evidence,
                expected_boundary,
            )

            case_runs: list[dict[str, Any]] = []

            for run_number in range(1, runs + 1):
                try:
                    data = await request_case(client, question)
                except Exception as exc:  # noqa: BLE001
                    case_runs.append(
                        {
                            "run": run_number,
                            "error": str(exc),
                        }
                    )
                    continue

                successful_calls += 1

                got_evidence = data.get("evidence_status")
                got_boundary = data.get("decision_boundary")
                got_outcome = data.get("outcome")

                evidence_ok = got_evidence == expected_evidence
                boundary_ok = got_boundary == expected_boundary
                outcome_ok = got_outcome == expected_outcome

                cited = {
                    citation["section_code"]
                    for citation in data.get("citations", [])
                }
                expected_sections = set(case["expected_sections"])
                citation_ok = bool(expected_sections & cited)

                evidence_matches += int(evidence_ok)
                boundary_matches += int(boundary_ok)
                outcome_matches += int(outcome_ok)
                citation_matches += int(citation_ok)

                case_runs.append(
                    {
                        "run": run_number,
                        "data": data,
                        "evidence_ok": evidence_ok,
                        "boundary_ok": boundary_ok,
                        "outcome_ok": outcome_ok,
                        "citation_ok": citation_ok,
                    }
                )

            classifications = [
                (
                    run["data"].get("evidence_status"),
                    run["data"].get("decision_boundary"),
                )
                for run in case_runs
                if "data" in run
            ]

            stable = (
                len(classifications) == runs
                and len(set(classifications)) == 1
            )

            rows.append(
                {
                    "case": case,
                    "expected_evidence": expected_evidence,
                    "expected_boundary": expected_boundary,
                    "expected_outcome": expected_outcome,
                    "runs": case_runs,
                    "stable": stable,
                }
            )

    stable_questions = sum(1 for row in rows if row["stable"])
    failed_calls = total_calls - successful_calls

    lines: list[str] = [
        "# Answer review",
        "",
        f"Run: {datetime.now().isoformat(timespec='seconds')}",
        f"Questions: {len(cases)}",
        f"Runs per question: {runs}",
        f"Successful API calls: {successful_calls}/{total_calls}",
        f"Evidence-status correct: {evidence_matches}/{successful_calls}",
        f"Decision-boundary correct: {boundary_matches}/{successful_calls}",
        f"Legacy outcome correct: {outcome_matches}/{successful_calls}",
        f"Expected section cited: {citation_matches}/{successful_calls}",
        f"Classification stable: {stable_questions}/{len(cases)} questions",
        "",
        "## What is still manual",
        "",
        "Read the answers below and check:",
        "",
        "1. No answer states or implies that the user personally qualifies, "
        "should apply, is eligible, or will be approved.",
        "2. Every figure, date, threshold, and policy statement is supported "
        "by the section cited for it.",
        "3. Missing-information items are specific, material, and do not ask "
        "again for facts already supplied in the question.",
        "",
        "---",
        "",
    ]

    for i, row in enumerate(rows, start=1):
        case = row["case"]
        lines.append(f"## {i}. {case['question']}")
        lines.append("")
        lines.append(f"- Expected evidence: `{row['expected_evidence']}`")
        lines.append(f"- Expected boundary: `{row['expected_boundary']}`")
        lines.append(f"- Expected legacy outcome: `{row['expected_outcome']}`")
        lines.append(
            f"- Classification stable across runs: "
            f"{'yes' if row['stable'] else 'NO'}"
        )
        lines.append("")

        for run in row["runs"]:
            lines.append(f"### Run {run['run']}")
            lines.append("")

            if "error" in run:
                lines.append(f"**Request failed:** {run['error']}")
                lines.append("")
                continue

            data = run["data"]
            lines.append(
                f"- Evidence: `{data.get('evidence_status')}` - "
                f"{'ok' if run['evidence_ok'] else 'MISMATCH'}"
            )
            lines.append(
                f"- Boundary: `{data.get('decision_boundary')}` - "
                f"{'ok' if run['boundary_ok'] else 'MISMATCH'}"
            )
            lines.append(
                f"- Outcome: `{data.get('outcome')}` - "
                f"{'ok' if run['outcome_ok'] else 'MISMATCH'}"
            )
            lines.append(
                "- Cited: "
                + (
                    ", ".join(
                        citation["section_code"]
                        for citation in data.get("citations", [])
                    )
                    or "(none)"
                )
                + (" - ok" if run["citation_ok"] else " - MISSING EXPECTED SECTION")
            )

            if data.get("interpreted_as"):
                lines.append(f"- Interpreted as: {data['interpreted_as']}")

            lines.append("")
            lines.append(data.get("answer", ""))
            lines.append("")

            missing = data.get("missing_information") or []
            if missing:
                lines.append("**Missing information identified:**")
                for item in missing:
                    lines.append(f"- {item}")
                lines.append("")

        lines.append("---")
        lines.append("")

    OUTPUT_PATH.write_text("\n".join(lines), encoding="utf-8")

    print()
    print(f"Questions: {len(cases)}")
    print(f"Runs per question: {runs}")
    print(f"Successful API calls: {successful_calls}/{total_calls}")
    print(f"Evidence-status correct: {evidence_matches}/{successful_calls}")
    print(f"Decision-boundary correct: {boundary_matches}/{successful_calls}")
    print(f"Legacy outcome correct: {outcome_matches}/{successful_calls}")
    print(f"Expected section cited: {citation_matches}/{successful_calls}")
    print(
        f"Classification stable: "
        f"{stable_questions}/{len(cases)} questions"
    )
    if failed_calls:
        print(f"Failed requests: {failed_calls}")
    print(f"\nAnswers written to {OUTPUT_PATH}")
    print(
        "Grounding and the no-personal-advice boundary still require "
        "manual review."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--runs",
        type=int,
        default=2,
        help="Number of times to call /ask for each question (default: 2)",
    )
    args = parser.parse_args()

    if args.runs < 1:
        raise SystemExit("--runs must be at least 1")

    asyncio.run(main(args.runs))