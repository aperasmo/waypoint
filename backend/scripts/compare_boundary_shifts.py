"""Compare production chunk boundaries with local semantic boundary shifts.

Read-only experiment. It never changes:
- app/ingestion/chunker.py
- corpus markdown
- data/manifest.json
- PostgreSQL
- stored embeddings

Hard invariant:
    candidate chunk count == production chunk count

Candidate rule:
- reproduce every production split boundary;
- for each existing boundary, look only within +/- 600 source characters;
- if a safe legal boundary exists there, select the one with the strongest
  adjacent semantic distance;
- otherwise retain the production boundary;
- never add or remove a boundary;
- preserve the same 200-character overlap.

Run from backend/:
    uv run python -m scripts.compare_boundary_shifts

Optional:
    uv run python -m scripts.compare_boundary_shifts --section SR2.10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from statistics import median

import frontmatter

from app.ingestion.chunker import (
    MAX_CHARS,
    OVERLAP_CHARS,
    chunk_corpus,
    drop_repeated_title,
    normalise,
    strip_navigation,
)
from app.ingestion.embedder import OpenAIEmbedder


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_MANIFEST = REPO_ROOT / "data" / "manifest.json"

SHIFT_WINDOW_CHARS = 600

SECTION_HEADING_RE = re.compile(
    r"^[A-Z]{1,4}\d+(?:\.\d+)+(?:\.\d+)*\s+\S+"
)
ROOT_CLAUSE_RE = re.compile(r"^\([a-z0-9]+\)\s+", re.IGNORECASE)
LABEL_RE = re.compile(r"^(?:Note|Notes|Example|Examples):?$", re.IGNORECASE)


@dataclass(frozen=True)
class SectionBody:
    section_code: str
    title: str
    body: str
    baseline_chunks: list[str]


@dataclass(frozen=True)
class LegalUnit:
    start_line: int
    text: str


@dataclass(frozen=True)
class BoundaryShift:
    section_code: str
    boundary_number: int
    baseline_line: int
    candidate_line: int
    shift_chars: int
    semantic_distance: float
    candidate_right_text: str


@dataclass(frozen=True)
class ShiftDiagnostic:
    section_code: str
    boundary_number: int
    shift_chars: int
    semantic_distance: float
    production_left_chars: int
    production_right_chars: int
    candidate_left_chars: int
    candidate_right_chars: int

    @property
    def production_imbalance(self) -> int:
        return abs(self.production_left_chars - self.production_right_chars)

    @property
    def candidate_imbalance(self) -> int:
        return abs(self.candidate_left_chars - self.candidate_right_chars)

    @property
    def imbalance_delta(self) -> int:
        return self.candidate_imbalance - self.production_imbalance


def source_lines(text: str) -> list[str]:
    """Match production split_text(): blank lines are ignored."""
    return [line for line in text.split("\n") if line.strip()]


def boundary_offsets(lines: list[str]) -> list[int]:
    """Character offset at the start of each source line."""
    offsets: list[int] = []
    position = 0
    for i, line in enumerate(lines):
        offsets.append(position)
        position += len(line)
        if i < len(lines) - 1:
            position += 1
    return offsets


def production_boundary_lines(
    text: str,
    max_chars: int = MAX_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> list[int]:
    """Mirror split_text() while recording source-line split positions.

    A returned index i means the production boundary occurs immediately
    before source line i.
    """
    if len(text) <= max_chars:
        return []

    lines = source_lines(text)
    boundaries: list[int] = []
    current = ""

    for i, para in enumerate(lines):
        candidate = f"{current}\n{para}" if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            boundaries.append(i)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n{para}" if tail else para
        else:
            current = para

    return boundaries


def starts_legal_block(line: str) -> bool:
    stripped = line.strip()

    # Indented roman/nested clauses remain attached to the parent root clause.
    if line[:1].isspace():
        return False

    return bool(
        ROOT_CLAUSE_RE.match(stripped)
        or SECTION_HEADING_RE.match(stripped)
        or LABEL_RE.match(stripped)
    )


def legal_units(text: str) -> list[LegalUnit]:
    """Build coherent legal blocks and retain their source-line start indexes."""
    lines = source_lines(text)
    units: list[LegalUnit] = []
    current: list[str] = []
    current_start = 0
    i = 0

    def flush() -> None:
        nonlocal current
        if current:
            units.append(
                LegalUnit(
                    start_line=current_start,
                    text="\n".join(current).strip(),
                )
            )
            current = []

    while i < len(lines):
        line = lines[i]

        # A converted Markdown table is one legal unit.
        if line.lstrip().startswith("|"):
            flush()
            table_start = i
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            units.append(
                LegalUnit(
                    start_line=table_start,
                    text="\n".join(table_lines).strip(),
                )
            )
            continue

        if starts_legal_block(line):
            flush()
            current_start = i
        elif not current:
            current_start = i

        current.append(line)
        i += 1

    flush()
    return units


def cosine_distance(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError(f"Embedding dimension mismatch: {len(a)} != {len(b)}")

    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))

    if norm_a == 0.0 or norm_b == 0.0:
        raise ValueError("Cannot compute cosine distance for a zero vector")

    return 1.0 - dot / (norm_a * norm_b)


def rebuild_chunks(
    lines: list[str],
    boundaries: list[int],
    overlap: int = OVERLAP_CHARS,
) -> list[str]:
    """Rebuild chunks from source-line boundaries with production overlap."""
    starts = [0, *boundaries]
    ends = [*boundaries, len(lines)]
    chunks: list[str] = []
    previous = ""

    for start, end in zip(starts, ends, strict=True):
        core = "\n".join(lines[start:end]).strip()

        if chunks and overlap:
            tail = previous[-overlap:]
            chunk = f"{tail}\n{core}" if core else tail
        else:
            chunk = core

        chunks.append(chunk)
        previous = chunk

    return chunks


def load_sections(manifest_path: Path) -> tuple[list[SectionBody], int]:
    baseline, _ = chunk_corpus(manifest_path)

    by_code: dict[str, list] = {}
    for chunk in baseline:
        by_code.setdefault(chunk.section_code, []).append(chunk)

    for chunks in by_code.values():
        chunks.sort(key=lambda c: c.chunk_index)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["pages"] if isinstance(manifest, dict) else manifest
    corpus_dir = manifest_path.parent

    sections: list[SectionBody] = []

    for entry in entries:
        code = str(entry["section_code"])
        baseline_chunks = by_code.get(code, [])
        if not baseline_chunks:
            continue

        path = corpus_dir / Path(str(entry["file"]).replace("\\", "/"))
        if not path.exists():
            continue

        post = frontmatter.load(path)
        title = str(post.get("title") or entry.get("title") or code)

        body = strip_navigation(post.content)
        body = drop_repeated_title(body, title)
        body = normalise(body)

        if not body:
            continue

        sections.append(
            SectionBody(
                section_code=code,
                title=title,
                body=body,
                baseline_chunks=[c.text for c in baseline_chunks],
            )
        )

    return sections, len(baseline)


async def compare(
    manifest_path: Path,
    section_filter: str | None,
    shift_window: int,
) -> None:
    sections, production_total = load_sections(manifest_path)

    if section_filter:
        sections = [s for s in sections if s.section_code == section_filter]
        if not sections:
            raise SystemExit(f"Section not found: {section_filter}")

    split_sections = [s for s in sections if len(s.baseline_chunks) > 1]

    units_by_code: dict[str, list[LegalUnit]] = {}
    inputs: list[str] = []
    locations: list[tuple[str, int]] = []

    for section in split_sections:
        units = legal_units(section.body)
        units_by_code[section.section_code] = units

        for i, unit in enumerate(units):
            inputs.append(
                f"{section.section_code}: {section.title}\n\n{unit.text}"
            )
            locations.append((section.section_code, i))

    embedder = OpenAIEmbedder()

    print("Waypoint semantic boundary-shift comparator")
    print("=" * 43)
    print(f"Manifest:                  {manifest_path}")
    print(f"Production MAX_CHARS:      {MAX_CHARS}")
    print(f"Production overlap:        {OVERLAP_CHARS}")
    print(f"Local shift window:        +/- {shift_window} chars")
    print(f"Sections inspected:        {len(sections)}")
    print(f"Production split sections: {len(split_sections)}")
    print(f"Legal units embedded:      {len(inputs)}")
    print(f"Embedding model:           {embedder.model_name}")
    print()
    print("Embedding legal units...")

    vectors = await embedder.embed_documents(inputs)
    if len(vectors) != len(inputs):
        raise RuntimeError(
            f"Expected {len(inputs)} embeddings, got {len(vectors)}"
        )

    vectors_by_location = dict(zip(locations, vectors, strict=True))

    shifts: list[BoundaryShift] = []
    shift_diagnostics: list[ShiftDiagnostic] = []
    total_boundaries = 0
    candidate_total = 0
    production_lengths: list[int] = []
    candidate_lengths: list[int] = []
    smallest_candidate: tuple[str, int, int] | None = None
    sections_shifted: set[str] = set()
    invariant_errors: list[str] = []

    for section in sections:
        baseline_count = len(section.baseline_chunks)
        production_lengths.extend(len(chunk) for chunk in section.baseline_chunks)

        if baseline_count == 1:
            candidate_total += 1
            candidate_lengths.append(len(section.body))
            if smallest_candidate is None or len(section.body) < smallest_candidate[2]:
                smallest_candidate = (section.section_code, 1, len(section.body))
            continue

        lines = source_lines(section.body)
        offsets = boundary_offsets(lines)
        baseline_boundaries = production_boundary_lines(section.body)
        total_boundaries += len(baseline_boundaries)

        if len(baseline_boundaries) != baseline_count - 1:
            invariant_errors.append(
                f"{section.section_code}: production boundaries="
                f"{len(baseline_boundaries)}, expected={baseline_count - 1}"
            )
            continue

        units = units_by_code[section.section_code]

        # Semantic score exists at the start of each legal unit except the first.
        safe_scores: dict[int, float] = {}
        safe_right_text: dict[int, str] = {}

        for i in range(1, len(units)):
            line_index = units[i].start_line
            safe_scores[line_index] = cosine_distance(
                vectors_by_location[(section.section_code, i - 1)],
                vectors_by_location[(section.section_code, i)],
            )
            safe_right_text[line_index] = units[i].text

        candidate_boundaries: list[int] = []

        for boundary_position, baseline_line in enumerate(
            baseline_boundaries, start=1
        ):
            baseline_offset = offsets[baseline_line]

            # Midpoint guards ensure independently shifted boundaries can
            # never cross or collapse into each other.
            previous_offset = (
                offsets[baseline_boundaries[boundary_position - 2]]
                if boundary_position > 1
                else 0
            )
            next_offset = (
                offsets[baseline_boundaries[boundary_position]]
                if boundary_position < len(baseline_boundaries)
                else len(section.body)
            )

            lower_guard = (previous_offset + baseline_offset) // 2
            upper_guard = (baseline_offset + next_offset) // 2

            eligible: list[tuple[float, int, int]] = []

            for safe_line, distance in safe_scores.items():
                safe_offset = offsets[safe_line]
                delta = safe_offset - baseline_offset

                if abs(delta) > shift_window:
                    continue
                if not lower_guard < safe_offset < upper_guard:
                    continue

                eligible.append(
                    (
                        distance,
                        -abs(delta),  # closer wins an exact distance tie
                        safe_line,
                    )
                )

            chosen_line = baseline_line

            if eligible:
                distance, _, safe_line = max(
                    eligible,
                    key=lambda item: (item[0], item[1]),
                )

                if safe_line != baseline_line:
                    chosen_line = safe_line
                    shift_chars = offsets[safe_line] - baseline_offset

                    shifts.append(
                        BoundaryShift(
                            section_code=section.section_code,
                            boundary_number=boundary_position,
                            baseline_line=baseline_line,
                            candidate_line=safe_line,
                            shift_chars=shift_chars,
                            semantic_distance=distance,
                            candidate_right_text=safe_right_text[safe_line],
                        )
                    )
                    sections_shifted.add(section.section_code)

            candidate_boundaries.append(chosen_line)

        # Hard invariant: one candidate boundary per production boundary.
        if len(candidate_boundaries) != len(baseline_boundaries):
            invariant_errors.append(
                f"{section.section_code}: candidate boundary count changed"
            )
            continue

        if candidate_boundaries != sorted(candidate_boundaries):
            invariant_errors.append(
                f"{section.section_code}: candidate boundaries not ordered"
            )
            continue

        if len(set(candidate_boundaries)) != len(candidate_boundaries):
            invariant_errors.append(
                f"{section.section_code}: duplicate candidate boundary"
            )
            continue

        candidate_chunks = rebuild_chunks(
            lines,
            candidate_boundaries,
            OVERLAP_CHARS,
        )

        if len(candidate_chunks) != baseline_count:
            invariant_errors.append(
                f"{section.section_code}: candidate chunks="
                f"{len(candidate_chunks)}, production={baseline_count}"
            )
            continue

        candidate_total += len(candidate_chunks)
        candidate_lengths.extend(len(c) for c in candidate_chunks)

        for idx, chunk in enumerate(candidate_chunks, start=1):
            length = len(chunk)
            if smallest_candidate is None or length < smallest_candidate[2]:
                smallest_candidate = (section.section_code, idx, length)

        # Compare the two chunks adjacent to each shifted boundary only.
        shifted_by_number = {
            shift.boundary_number: shift
            for shift in shifts
            if shift.section_code == section.section_code
        }

        for boundary_number, shift in shifted_by_number.items():
            left_index = boundary_number - 1
            right_index = boundary_number

            if right_index >= baseline_count:
                invariant_errors.append(
                    f"{section.section_code}: invalid shifted boundary "
                    f"{boundary_number}"
                )
                continue

            shift_diagnostics.append(
                ShiftDiagnostic(
                    section_code=section.section_code,
                    boundary_number=boundary_number,
                    shift_chars=shift.shift_chars,
                    semantic_distance=shift.semantic_distance,
                    production_left_chars=len(section.baseline_chunks[left_index]),
                    production_right_chars=len(section.baseline_chunks[right_index]),
                    candidate_left_chars=len(candidate_chunks[left_index]),
                    candidate_right_chars=len(candidate_chunks[right_index]),
                )
            )

    expected_total = (
        sum(len(s.baseline_chunks) for s in sections)
        if section_filter
        else production_total
    )

    print()
    print("Summary")
    print("-" * 76)
    print(f"Production chunks:         {expected_total}")
    print(f"Candidate chunks:          {candidate_total}")
    print(f"Chunk-count delta:         {candidate_total - expected_total:+d}")
    print(f"Production boundaries:     {total_boundaries}")
    print(f"Shifted boundaries:        {len(shifts)}")
    print(f"Unchanged boundaries:      {total_boundaries - len(shifts)}")
    print(f"Sections with shifts:      {len(sections_shifted)}")

    if shifts:
        magnitudes = [abs(s.shift_chars) for s in shifts]
        print(f"Median boundary shift:     {int(median(magnitudes))} chars")
        print(f"Maximum boundary shift:    {max(magnitudes)} chars")

    if production_lengths and candidate_lengths:
        print()
        print("Chunk-size distribution")
        print("-" * 76)
        print(
            f"Production chars:          "
            f"min={min(production_lengths):<5} "
            f"median={int(median(production_lengths)):<5} "
            f"max={max(production_lengths)}"
        )
        print(
            f"Candidate chars:           "
            f"min={min(candidate_lengths):<5} "
            f"median={int(median(candidate_lengths)):<5} "
            f"max={max(candidate_lengths)}"
        )

        if smallest_candidate is not None:
            code, chunk_number, length = smallest_candidate
            matching_section = next(
                s for s in sections if s.section_code == code
            )
            production_same_position = (
                len(matching_section.baseline_chunks[chunk_number - 1])
                if chunk_number <= len(matching_section.baseline_chunks)
                else None
            )
            print(
                f"Smallest candidate:        {code} chunk {chunk_number} "
                f"= {length} chars"
            )
            if production_same_position is not None:
                print(
                    f"Production same position:  "
                    f"{production_same_position} chars"
                )

    if invariant_errors:
        print()
        print("INVARIANT FAILURES")
        print("-" * 76)
        for error in invariant_errors:
            print(error)
        raise SystemExit(
            "Boundary-shift candidate rejected: invariant failure."
        )

    if candidate_total != expected_total:
        raise SystemExit(
            "Boundary-shift candidate rejected: chunk-count invariant failed."
        )

    print()
    print("Chunk-count invariant:     PASS")

    if shift_diagnostics:
        improved = sum(1 for d in shift_diagnostics if d.imbalance_delta < 0)
        unchanged = sum(1 for d in shift_diagnostics if d.imbalance_delta == 0)
        worsened = sum(1 for d in shift_diagnostics if d.imbalance_delta > 0)

        print()
        print("Boundary balance diagnostics")
        print("-" * 76)
        print(f"Shifted boundaries tested: {len(shift_diagnostics)}")
        print(f"Balance improved:          {improved}")
        print(f"Balance unchanged:         {unchanged}")
        print(f"Balance worsened:          {worsened}")
        print(
            f"Median imbalance delta:    "
            f"{int(median([d.imbalance_delta for d in shift_diagnostics])):+d} chars"
        )

        print()
        print("Most worsened shifted boundaries")
        print("-" * 76)
        for d in sorted(
            shift_diagnostics,
            key=lambda item: item.imbalance_delta,
            reverse=True,
        )[:10]:
            direction = "+" if d.shift_chars > 0 else ""
            print(
                f"{d.section_code:<10} "
                f"boundary={d.boundary_number:<2} "
                f"shift={direction}{d.shift_chars:<5} "
                f"distance={d.semantic_distance:.6f} "
                f"imbalance_delta={d.imbalance_delta:+d}"
            )
            print(
                f"    production: "
                f"{d.production_left_chars} / {d.production_right_chars} chars"
            )
            print(
                f"    candidate : "
                f"{d.candidate_left_chars} / {d.candidate_right_chars} chars"
            )

    if shifts:
        print()
        print("Shifted boundaries")
        print("-" * 76)

        for shift in sorted(
            shifts,
            key=lambda item: (
                -item.semantic_distance,
                item.section_code,
                item.boundary_number,
            ),
        ):
            direction = "+" if shift.shift_chars > 0 else ""
            right = " ".join(shift.candidate_right_text.split())
            if len(right) > 92:
                right = right[:89] + "..."

            print(
                f"{shift.section_code:<10} "
                f"boundary={shift.boundary_number:<2} "
                f"shift={direction}{shift.shift_chars:<5} "
                f"distance={shift.semantic_distance:.6f}"
            )
            print(f"    next legal block: {right}")

    print()
    print(
        "Read-only comparison complete. "
        "No corpus or database rows were changed."
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Move existing production boundaries only to nearby semantic "
            "legal boundaries while preserving chunk count."
        )
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
    )
    parser.add_argument("--section")
    parser.add_argument(
        "--window",
        type=int,
        default=SHIFT_WINDOW_CHARS,
        help="Maximum source-character movement on either side (default: 600).",
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        parser.error(f"manifest not found: {args.manifest}")
    if args.window < 0:
        parser.error("--window must be zero or greater")

    asyncio.run(
        compare(
            manifest_path=args.manifest,
            section_filter=args.section,
            shift_window=args.window,
        )
    )


if __name__ == "__main__":
    main()