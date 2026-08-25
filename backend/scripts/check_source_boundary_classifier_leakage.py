"""Leakage guard for the Waypoint experimental source-boundary classifier bundle.

This guard performs static checks only. It makes no model calls.

Run from backend/:
    uv run python -m py_compile scripts/check_source_boundary_classifier_leakage.py
    uv run python -m scripts.check_source_boundary_classifier_leakage
"""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent

CLASSIFIER_PATH = (
    BACKEND_DIR
    / "_experiments"
    / "source_boundary_classifier_v1.py"
)

RUNNER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "run_source_boundary_classifier_contract_v1.py"
)

SCORER_PATH = (
    BACKEND_DIR
    / "scripts"
    / "score_source_boundary_classifier_contract_v1.py"
)

EXPECTED_CLASSIFIER_SHA256 = (
    "BC77C28033F74E3092C8428DE623293D"
    "266FBDEE7FFC237EE79C8AB6F79DE9F3"
)

EXPECTED_RUNNER_SHA256 = (
    "CE2709C654E576B56520AAD7CA9DB90A"
    "88E80CF775C3B8AC7A3864669F610FEF"
)

EXPECTED_SCORER_SHA256 = (
    "19563B4DD326CCB1E5DA125F30625915"
    "FB2BE197786640FA6223BFB44855FE46"
)

ALLOWED_RUNNER_CASE_FIELDS = {
    "test_id",
    "unsupported_proposition",
    "trusted_source_context",
}

FORBIDDEN_CLASSIFIER_IMPORT_ROOTS = {
    "app",
    "tests",
    "sqlalchemy",
    "pgvector",
}

FORBIDDEN_SCORER_IMPORT_ROOTS = {
    "openai",
    "app",
    "_experiments",
    "sqlalchemy",
    "pgvector",
}

FORBIDDEN_CLASSIFIER_STRING_FRAGMENTS = {
    "source_boundary_classifier_contract_test_pack",
    "source_boundary_classifier_acceptance_thresholds",
    "source_boundary_classifier_predictions",
    "source_boundary_classifier_score",
    "external_adjudication",
    "external_predictions",
    "failure_inventory",
    "failure_taxonomy",
    "expected_sections",
    "adjudication_note",
}

FORBIDDEN_CLASSIFIER_IDENTIFIERS = {
    "test_id",
    "expected_output",
    "expected_sections",
    "gold",
    "gold_status",
    "contrast_group",
    "acceptance_threshold",
    "hard_gates",
}

BENCHMARK_ID_RE = re.compile(
    r"\bext2?_[0-9a-f]{16}\b",
    flags=re.IGNORECASE,
)

SYNTHETIC_TEST_ID_RE = re.compile(
    r"\bsbv\d+_\d+\b",
    flags=re.IGNORECASE,
)

MANUAL_SECTION_RE = re.compile(
    r"\b(?:A|R|SR|U|V|WA|WD)\d+(?:\.\d+)+\b"
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def require_sha(
    path: Path,
    expected: str,
    label: str,
) -> None:
    if not path.exists():
        raise SystemExit(f"Required file not found: {path}")

    actual = sha256(path)

    if actual != expected:
        raise SystemExit(
            f"{label} SHA mismatch.\n"
            f"Path:     {path}\n"
            f"Expected: {expected}\n"
            f"Actual:   {actual}\n"
            "Leakage guard aborted."
        )


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_tree(path: Path) -> ast.AST:
    try:
        return ast.parse(
            read_text(path),
            filename=str(path),
        )
    except SyntaxError as exc:
        raise RuntimeError(
            f"Syntax error while parsing {path}: {exc}"
        ) from exc


def imported_roots(tree: ast.AST) -> set[str]:
    roots: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".", 1)[0])

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                roots.add(node.module.split(".", 1)[0])

    return roots


def string_literals(tree: ast.AST) -> list[str]:
    values: list[str] = []

    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
        ):
            values.append(node.value)

    return values


def identifier_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.add(node.id)

        elif isinstance(node, ast.arg):
            names.add(node.arg)

        elif isinstance(node, ast.FunctionDef):
            names.add(node.name)

        elif isinstance(node, ast.AsyncFunctionDef):
            names.add(node.name)

        elif isinstance(node, ast.ClassDef):
            names.add(node.name)

    return names


def find_regex_hits(
    *,
    text: str,
    regex: re.Pattern[str],
) -> list[str]:
    return sorted(set(regex.findall(text)))


def check_classifier() -> None:
    tree = parse_tree(CLASSIFIER_PATH)
    text = read_text(CLASSIFIER_PATH)

    roots = imported_roots(tree)
    forbidden_imports = sorted(
        roots & FORBIDDEN_CLASSIFIER_IMPORT_ROOTS
    )

    if forbidden_imports:
        raise RuntimeError(
            "Classifier imports forbidden runtime/evaluation roots: "
            f"{forbidden_imports}"
        )

    strings = string_literals(tree)
    lowered_strings = [
        value.casefold()
        for value in strings
    ]

    leaked_fragments = sorted(
        fragment
        for fragment in FORBIDDEN_CLASSIFIER_STRING_FRAGMENTS
        if any(
            fragment.casefold() in value
            for value in lowered_strings
        )
    )

    if leaked_fragments:
        raise RuntimeError(
            "Classifier contains forbidden evaluation/source fragments: "
            f"{leaked_fragments}"
        )

    names = {
        name.casefold()
        for name in identifier_names(tree)
    }

    leaked_identifiers = sorted(
        identifier
        for identifier in FORBIDDEN_CLASSIFIER_IDENTIFIERS
        if identifier.casefold() in names
    )

    if leaked_identifiers:
        raise RuntimeError(
            "Classifier contains forbidden evaluation identifiers: "
            f"{leaked_identifiers}"
        )

    benchmark_hits = find_regex_hits(
        text=text,
        regex=BENCHMARK_ID_RE,
    )

    if benchmark_hits:
        raise RuntimeError(
            f"Classifier contains retired benchmark IDs: {benchmark_hits}"
        )

    synthetic_hits = find_regex_hits(
        text=text,
        regex=SYNTHETIC_TEST_ID_RE,
    )

    if synthetic_hits:
        raise RuntimeError(
            f"Classifier contains synthetic contract IDs: {synthetic_hits}"
        )

    section_hits = find_regex_hits(
        text=text,
        regex=MANUAL_SECTION_RE,
    )

    if section_hits:
        raise RuntimeError(
            f"Classifier contains Manual section literals: {section_hits}"
        )

    required_call_markers = (
        "chat.completions.create",
        "temperature=0",
        'response_format={"type": "json_object"}',
        "CLASSIFIER_REASONING_EFFORT",
        "CLASSIFIER_MAX_COMPLETION_TOKENS",
    )

    missing_markers = [
        marker
        for marker in required_call_markers
        if marker not in text
    ]

    if missing_markers:
        raise RuntimeError(
            "Classifier is missing frozen model-call markers: "
            f"{missing_markers}"
        )

    forbidden_retry_markers = (
        "tenacity",
        "backoff",
        "retrying",
    )

    retry_hits = [
        marker
        for marker in forbidden_retry_markers
        if marker.casefold() in text.casefold()
    ]

    if retry_hits:
        raise RuntimeError(
            "Classifier contains retry-library markers: "
            f"{retry_hits}"
        )


def _subscript_key(node: ast.Subscript) -> str | None:
    slice_node = node.slice

    if (
        isinstance(slice_node, ast.Constant)
        and isinstance(slice_node.value, str)
    ):
        return slice_node.value

    return None


def _constant_string_arg(
    call: ast.Call,
    position: int = 0,
) -> str | None:
    if len(call.args) <= position:
        return None

    value = call.args[position]

    if (
        isinstance(value, ast.Constant)
        and isinstance(value.value, str)
    ):
        return value.value

    return None


def check_runner() -> None:
    tree = parse_tree(RUNNER_PATH)
    text = read_text(RUNNER_PATH)

    benchmark_hits = find_regex_hits(
        text=text,
        regex=BENCHMARK_ID_RE,
    )

    if benchmark_hits:
        raise RuntimeError(
            f"Runner contains retired benchmark IDs: {benchmark_hits}"
        )

    synthetic_hits = find_regex_hits(
        text=text,
        regex=SYNTHETIC_TEST_ID_RE,
    )

    if synthetic_hits:
        raise RuntimeError(
            f"Runner contains hard-coded synthetic IDs: {synthetic_hits}"
        )

    section_hits = find_regex_hits(
        text=text,
        regex=MANUAL_SECTION_RE,
    )

    if section_hits:
        raise RuntimeError(
            f"Runner contains Manual section literals: {section_hits}"
        )

    roots = imported_roots(tree)

    if "tests" in roots:
        raise RuntimeError(
            "Runner must not import tests as Python modules."
        )

    # Validate all direct field reads from the contract test variable `case`.
    observed_case_fields: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func

            if (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and isinstance(func.value, ast.Name)
                and func.value.id == "case"
            ):
                key = _constant_string_arg(node)

                if key is not None:
                    observed_case_fields.add(key)

        elif isinstance(node, ast.Subscript):
            if (
                isinstance(node.value, ast.Name)
                and node.value.id == "case"
            ):
                key = _subscript_key(node)

                if key is not None:
                    observed_case_fields.add(key)

    unexpected_case_fields = sorted(
        observed_case_fields
        - ALLOWED_RUNNER_CASE_FIELDS
    )

    if unexpected_case_fields:
        raise RuntimeError(
            "Runner reads unauthorised contract-pack case fields: "
            f"{unexpected_case_fields}"
        )

    missing_case_fields = sorted(
        ALLOWED_RUNNER_CASE_FIELDS
        - observed_case_fields
    )

    if missing_case_fields:
        raise RuntimeError(
            "Runner is missing authorised blind case fields: "
            f"{missing_case_fields}"
        )

    # Ensure test_id is not passed to the classifier call.
    classifier_calls: list[ast.Call] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        if (
            isinstance(func, ast.Name)
            and func.id == "classify_source_boundary"
        ):
            classifier_calls.append(node)

    if len(classifier_calls) != 1:
        raise RuntimeError(
            "Runner must contain exactly one classifier call site."
        )

    call = classifier_calls[0]
    keyword_names = {
        keyword.arg
        for keyword in call.keywords
        if keyword.arg is not None
    }

    expected_keywords = {
        "unsupported_proposition",
        "trusted_source_context",
        "model",
    }

    if keyword_names != expected_keywords:
        raise RuntimeError(
            "Runner classifier-call keyword set changed: "
            f"{sorted(keyword_names)}"
        )

    for keyword in call.keywords:
        value_dump = ast.dump(
            keyword.value,
            include_attributes=False,
        )

        if "test_id" in value_dump:
            raise RuntimeError(
                "Runner passes test_id into the classifier."
            )

    required_safety_markers = (
        "source_boundary_classifier_run_authorisation_v1.json",
        "Classifier contract run is NOT AUTHORISED.",
        "No model calls were made.",
        "single_run_only",
        "automatic_retry",
    )

    missing_safety_markers = [
        marker
        for marker in required_safety_markers
        if marker not in text
    ]

    if missing_safety_markers:
        raise RuntimeError(
            "Runner is missing execution-safety markers: "
            f"{missing_safety_markers}"
        )

    # No obvious gold/evaluation field access patterns from `case`.
    forbidden_case_fields = {
        "expected",
        "basis",
        "contrast_group",
        "gold",
        "expected_sections",
    }

    if observed_case_fields & forbidden_case_fields:
        raise RuntimeError(
            "Runner reads forbidden gold/scoring fields."
        )


def check_scorer() -> None:
    tree = parse_tree(SCORER_PATH)
    text = read_text(SCORER_PATH)

    roots = imported_roots(tree)
    forbidden_imports = sorted(
        roots & FORBIDDEN_SCORER_IMPORT_ROOTS
    )

    if forbidden_imports:
        raise RuntimeError(
            "Scorer imports forbidden runtime/model roots: "
            f"{forbidden_imports}"
        )

    model_call_markers = (
        "chat.completions.create",
        "responses.create",
        "AsyncOpenAI",
        "OpenAI(",
    )

    model_hits = [
        marker
        for marker in model_call_markers
        if marker in text
    ]

    if model_hits:
        raise RuntimeError(
            "Scorer contains model-call markers: "
            f"{model_hits}"
        )

    benchmark_hits = find_regex_hits(
        text=text,
        regex=BENCHMARK_ID_RE,
    )

    if benchmark_hits:
        raise RuntimeError(
            f"Scorer contains retired benchmark IDs: {benchmark_hits}"
        )

    section_hits = find_regex_hits(
        text=text,
        regex=MANUAL_SECTION_RE,
    )

    if section_hits:
        raise RuntimeError(
            f"Scorer contains Manual section literals: {section_hits}"
        )


def main() -> None:
    require_sha(
        CLASSIFIER_PATH,
        EXPECTED_CLASSIFIER_SHA256,
        "Experimental classifier",
    )
    require_sha(
        RUNNER_PATH,
        EXPECTED_RUNNER_SHA256,
        "Blind runner",
    )
    require_sha(
        SCORER_PATH,
        EXPECTED_SCORER_SHA256,
        "Scorer",
    )

    check_classifier()
    check_runner()
    check_scorer()

    print("Waypoint source-boundary classifier leakage guard")
    print("=" * 52)
    print(f"Classifier SHA256:          {sha256(CLASSIFIER_PATH)}")
    print(f"Runner SHA256:              {sha256(RUNNER_PATH)}")
    print(f"Scorer SHA256:              {sha256(SCORER_PATH)}")
    print()
    print("Classifier isolation")
    print("-" * 52)
    print("Production app imports:     NONE")
    print("Tests/gold imports:         NONE")
    print("Contract-pack references:   NONE")
    print("Threshold references:       NONE")
    print("Benchmark IDs:              NONE")
    print("Synthetic test IDs:         NONE")
    print("Manual section literals:    NONE")
    print()
    print("Blind runner")
    print("-" * 52)
    print("Authorised case fields:     EXACT")
    print("test_id passed to model:    NO")
    print("Expected/gold fields read:  NO")
    print("Benchmark IDs:              NONE")
    print("Synthetic hardcoding:       NONE")
    print("Manual section literals:    NONE")
    print("Run-authorisation gate:     PRESENT")
    print()
    print("Scorer")
    print("-" * 52)
    print("Model imports/calls:        NONE")
    print("Production imports:         NONE")
    print("Benchmark IDs:              NONE")
    print("Manual section literals:    NONE")
    print()
    print("Model calls:                NONE")
    print("Database writes:            NONE")
    print("Runtime files modified:     NONE")
    print()
    print("Source-boundary leakage guard: PASS")


if __name__ == "__main__":
    main()
