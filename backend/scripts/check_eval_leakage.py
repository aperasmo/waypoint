"""Detect direct evaluation leakage or section-specific hardcoding.

This is a read-only engineering guard for Waypoint.

It is intentionally conservative about the ranking path. It checks that:
1. production/runtime ranking code does not reference gold benchmark fields/files;
2. exact benchmark question text is not embedded in runtime/ranking code;
3. ranking code does not contain literal INZ section codes such as "U3.20";
4. runtime ranking code does not import from tests.

This cannot prove that a model/prompt has never been conceptually influenced by
development results. That methodological risk is handled separately through
blind prediction, frozen candidates, stability runs, and a fresh holdout.

Run from backend/:
    uv run python -m scripts.check_eval_leakage
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BACKEND_DIR / "app"
SCRIPTS_DIR = BACKEND_DIR / "scripts"
TESTS_DIR = BACKEND_DIR / "tests"

GOLD_FILES = (
    TESTS_DIR / "eval_questions.json",
    TESTS_DIR / "eval_questions_adjudicated_v2.json",
)

# Experimental scripts that make ranking decisions. Scoring/adjudication
# utilities are deliberately excluded because their job requires gold labels.
# BLIND_RANKING_SCRIPTS = (
#     SCRIPTS_DIR / "run_blind_reranker.py",
#     SCRIPTS_DIR / "freeze_blind_rerank_candidates.py",
#     SCRIPTS_DIR / "measure_reranker_stability.py",
# )

# Runtime files where section-specific ranking behaviour must never be encoded.
RANKING_RUNTIME_PATHS = (
    APP_DIR / "retrieval",
    APP_DIR / "api" / "ask.py",
)

FORBIDDEN_RUNTIME_MARKERS = (
    "expected_sections",
    "expected_section",
    "eval_questions.json",
    "eval_questions_adjudicated_v2.json",
    "rerank_questions_blind_v2.json",
    "rerank_candidates_blind_v2.json",
    "rerank_predictions_blind_v2.json",
    "rerank_stability_blind_v2.json",
)

SECTION_CODE_RE = re.compile(
    r"^(?:[A-Z]{1,4}\d+(?:\.\d+)+|[A-Z]{1,4}\d+)$"
)


def iter_python_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix == ".py" else []
    if path.is_dir():
        return sorted(path.rglob("*.py"))
    return []


def load_benchmark_questions() -> list[str]:
    questions: set[str] = set()

    for path in GOLD_FILES:
        if not path.exists():
            continue

        payload = json.loads(path.read_text(encoding="utf-8"))
        cases = payload.get("questions")

        if not isinstance(cases, list):
            raise RuntimeError(
                f"Unexpected benchmark schema in {path}: no questions list."
            )

        for case in cases:
            if not isinstance(case, dict):
                continue
            question = case.get("question")
            if isinstance(question, str) and question.strip():
                questions.add(question.strip())

    if not questions:
        raise RuntimeError(
            "No benchmark questions were found. Expected at least one of:\n"
            + "\n".join(str(path) for path in GOLD_FILES)
        )

    return sorted(questions)


def extract_string_literals(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    literals: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.append((getattr(node, "lineno", 0), node.value))

    return literals


def has_tests_import(path: Path) -> list[tuple[int, str]]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    findings: list[tuple[int, str]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tests" or alias.name.startswith("tests."):
                    findings.append(
                        (getattr(node, "lineno", 0), f"import {alias.name}")
                    )

        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "tests" or module.startswith("tests."):
                findings.append(
                    (
                        getattr(node, "lineno", 0),
                        f"from {module} import ...",
                    )
                )

    return findings


def main() -> None:
    questions = load_benchmark_questions()

    runtime_files: set[Path] = set()
    for path in RANKING_RUNTIME_PATHS:
        runtime_files.update(iter_python_files(path))

    # blind_files = {
    #     path for path in BLIND_RANKING_SCRIPTS if path.exists()
    # }

    if not runtime_files:
        raise SystemExit(
            "No runtime ranking files found under expected app paths."
        )

    # if not blind_files:
    #     raise SystemExit(
    #         "No blind ranking scripts found. Expected at least one of:\n"
    #         + "\n".join(str(path) for path in BLIND_RANKING_SCRIPTS)
    #     )

    failures: list[str] = []

    # ------------------------------------------------------------------
    # 1. Runtime ranking code must not know about eval/gold artifacts.
    # ------------------------------------------------------------------
    for path in sorted(runtime_files):
        source = path.read_text(encoding="utf-8")
        lowered = source.lower()

        for marker in FORBIDDEN_RUNTIME_MARKERS:
            if marker.lower() in lowered:
                failures.append(
                    f"{path}: forbidden runtime evaluation marker "
                    f"{marker!r}"
                )

        for lineno, statement in has_tests_import(path):
            failures.append(
                f"{path}:{lineno}: runtime import from tests: {statement}"
            )

    # ------------------------------------------------------------------
    # 2. Exact benchmark question text must not appear in runtime ranking code.
    # ------------------------------------------------------------------
    question_scan_files = runtime_files

    for path in sorted(question_scan_files):
        source = path.read_text(encoding="utf-8")

        for question in questions:
            if question in source:
                failures.append(
                    f"{path}: exact benchmark question embedded in ranking "
                    f"code: {question!r}"
                )

    # ------------------------------------------------------------------
    # 3. Section-code literals are prohibited in the runtime ranking path.
    #    Retrieval must infer relevance from the supplied evidence rather
    #    than from hand-written section preferences.
    # ------------------------------------------------------------------
    section_literal_files = runtime_files

    for path in sorted(section_literal_files):
        for lineno, literal in extract_string_literals(path):
            stripped = literal.strip()
            if SECTION_CODE_RE.fullmatch(stripped):
                failures.append(
                    f"{path}:{lineno}: hard-coded section-code literal "
                    f"{stripped!r}"
                )

    print("Waypoint evaluation leakage guard")
    print("=" * 33)
    print(f"Benchmark questions inspected: {len(questions)}")
    print(f"Runtime ranking files scanned: {len(runtime_files)}")
    print()
    print("Checks:")
    print("  runtime gold/eval references")
    print("  runtime imports from tests")
    print("  exact benchmark question literals")
    print("  hard-coded section-code literals in ranking paths")
    print()

    if failures:
        print("Result: FAIL")
        print("-" * 76)
        for failure in failures:
            print(f"- {failure}")
        raise SystemExit(1)

    print("Direct benchmark leakage found: none")
    print("Section-specific ranking literals found: none")
    print("Evaluation leakage guard: PASS")
    print()
    print(
        "Scope note: this guard detects direct code/data leakage and literal "
        "section hardcoding. Fresh holdout evaluation is still required to "
        "test generalisation and guard against conceptual overfitting."
    )


if __name__ == "__main__":
    main()