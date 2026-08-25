"""Constrained semantic boundary-shift comparator for Waypoint.

Read-only experiment. It never changes:
- app/ingestion/chunker.py
- corpus markdown
- data/manifest.json
- PostgreSQL
- stored embeddings

Hard invariants:
- candidate chunk count == production chunk count
- every candidate chunk <= production MAX_CHARS

Acceptance rule for a shifted production boundary:
1. A safe legal boundary must be within +/- 600 source characters.
2. Moving to it must keep every candidate chunk <= MAX_CHARS.
3. The local left/right chunk imbalance at every accepted shifted boundary
   must not be worse than production.
4. Among candidates passing those guards, the strongest semantic transition
   wins. Distance is a ranking signal, not a standalone trigger.
5. If nothing passes, retain the production boundary.

Run from backend/:
    uv run python -m scripts.compare_boundary_shifts_constrained
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
class AcceptedShift:
    section_code: str
    boundary_number: int
    shift_chars: int
    semantic_distance: float
    production_left_chars: int
    production_right_chars: int
    candidate_left_chars: int
    candidate_right_chars: int
    next_legal_block: str

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
    return [line for line in text.split("\n") if line.strip()]


def boundary_offsets(lines: list[str]) -> list[int]:
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
    if line[:1].isspace():
        return False
    return bool(
        ROOT_CLAUSE_RE.match(stripped)
        or SECTION_HEADING_RE.match(stripped)
        or LABEL_RE.match(stripped)
    )


def legal_units(text: str) -> list[LegalUnit]:
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


def imbalance(left: int, right: int) -> int:
    return abs(left - right)


def all_accepted_balances_safe(
    candidate_chunks: list[str],
    production_chunks: list[str],
    shifted_boundary_numbers: set[int],
) -> bool:
    """Ensure no already accepted shifted boundary becomes worse later."""
    for boundary_number in shifted_boundary_numbers:
        left = boundary_number - 1
        right = boundary_number

        production_balance = imbalance(
            len(production_chunks[left]),
            len(production_chunks[right]),
        )
        candidate_balance = imbalance(
            len(candidate_chunks[left]),
            len(candidate_chunks[right]),
        )

        if candidate_balance > production_balance:
            return False

    return True


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

    print("Waypoint constrained semantic boundary comparator")
    print("=" * 49)
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

    production_lengths: list[int] = []
    candidate_lengths: list[int] = []
    candidate_total = 0
    production_boundaries_total = 0
    accepted_shifts: list[AcceptedShift] = []
    sections_shifted: set[str] = set()
    invariant_errors: list[str] = []

    # Diagnostics for why possible semantic moves were rejected.
    rejected_size = 0
    rejected_balance = 0
    boundaries_with_no_safe_legal_candidate = 0

    for section in sections:
        production_lengths.extend(len(c) for c in section.baseline_chunks)
        baseline_count = len(section.baseline_chunks)

        if baseline_count == 1:
            candidate_total += 1
            candidate_lengths.append(len(section.body))
            continue

        lines = source_lines(section.body)
        offsets = boundary_offsets(lines)
        production_boundaries = production_boundary_lines(section.body)
        production_boundaries_total += len(production_boundaries)

        if len(production_boundaries) != baseline_count - 1:
            invariant_errors.append(
                f"{section.section_code}: production boundary count mismatch"
            )
            continue

        units = units_by_code[section.section_code]
        safe_scores: dict[int, float] = {}
        safe_right_text: dict[int, str] = {}

        for i in range(1, len(units)):
            line_index = units[i].start_line
            safe_scores[line_index] = cosine_distance(
                vectors_by_location[(section.section_code, i - 1)],
                vectors_by_location[(section.section_code, i)],
            )
            safe_right_text[line_index] = units[i].text

        chosen_boundaries = list(production_boundaries)
        accepted_numbers: set[int] = set()

        for boundary_number, production_line in enumerate(
            production_boundaries, start=1
        ):
            production_offset = offsets[production_line]

            previous_offset = (
                offsets[production_boundaries[boundary_number - 2]]
                if boundary_number > 1
                else 0
            )
            next_offset = (
                offsets[production_boundaries[boundary_number]]
                if boundary_number < len(production_boundaries)
                else len(section.body)
            )
            lower_guard = (previous_offset + production_offset) // 2
            upper_guard = (production_offset + next_offset) // 2

            nearby: list[tuple[float, int, int]] = []

            for safe_line, distance in safe_scores.items():
                safe_offset = offsets[safe_line]
                delta = safe_offset - production_offset

                if safe_line == production_line:
                    continue
                if abs(delta) > shift_window:
                    continue
                if not lower_guard < safe_offset < upper_guard:
                    continue

                nearby.append((distance, -abs(delta), safe_line))

            if not nearby:
                boundaries_with_no_safe_legal_candidate += 1
                continue

            accepted_this_boundary = False

            # Strongest semantic boundary first; closer movement breaks ties.
            for distance, _, safe_line in sorted(
                nearby,
                key=lambda item: (item[0], item[1]),
                reverse=True,
            ):
                trial_boundaries = list(chosen_boundaries)
                trial_boundaries[boundary_number - 1] = safe_line

                if trial_boundaries != sorted(trial_boundaries):
                    continue
                if len(set(trial_boundaries)) != len(trial_boundaries):
                    continue

                trial_chunks = rebuild_chunks(
                    lines,
                    trial_boundaries,
                    OVERLAP_CHARS,
                )

                if len(trial_chunks) != baseline_count:
                    continue

                # Guard 1: preserve the production hard size ceiling.
                if any(len(chunk) > MAX_CHARS for chunk in trial_chunks):
                    rejected_size += 1
                    continue

                # Guard 2: the proposed local boundary itself must not worsen
                # left/right balance relative to production.
                left = boundary_number - 1
                right = boundary_number

                production_balance = imbalance(
                    len(section.baseline_chunks[left]),
                    len(section.baseline_chunks[right]),
                )
                trial_balance = imbalance(
                    len(trial_chunks[left]),
                    len(trial_chunks[right]),
                )

                if trial_balance > production_balance:
                    rejected_balance += 1
                    continue

                # Guard 3: a later neighbouring move must not invalidate any
                # previously accepted shift in this section.
                trial_accepted = set(accepted_numbers)
                trial_accepted.add(boundary_number)

                if not all_accepted_balances_safe(
                    trial_chunks,
                    section.baseline_chunks,
                    trial_accepted,
                ):
                    rejected_balance += 1
                    continue

                chosen_boundaries = trial_boundaries
                accepted_numbers = trial_accepted
                accepted_this_boundary = True
                sections_shifted.add(section.section_code)

                shift_chars = offsets[safe_line] - production_offset
                accepted_shifts.append(
                    AcceptedShift(
                        section_code=section.section_code,
                        boundary_number=boundary_number,
                        shift_chars=shift_chars,
                        semantic_distance=distance,
                        production_left_chars=len(
                            section.baseline_chunks[left]
                        ),
                        production_right_chars=len(
                            section.baseline_chunks[right]
                        ),
                        candidate_left_chars=len(trial_chunks[left]),
                        candidate_right_chars=len(trial_chunks[right]),
                        next_legal_block=safe_right_text[safe_line],
                    )
                )
                break

            if not accepted_this_boundary:
                # Production boundary remains in place.
                pass

        candidate_chunks = rebuild_chunks(
            lines,
            chosen_boundaries,
            OVERLAP_CHARS,
        )

        if len(candidate_chunks) != baseline_count:
            invariant_errors.append(
                f"{section.section_code}: candidate chunk count changed"
            )
            continue

        if any(len(chunk) > MAX_CHARS for chunk in candidate_chunks):
            invariant_errors.append(
                f"{section.section_code}: candidate exceeds MAX_CHARS"
            )
            continue

        if not all_accepted_balances_safe(
            candidate_chunks,
            section.baseline_chunks,
            accepted_numbers,
        ):
            invariant_errors.append(
                f"{section.section_code}: accepted shift balance regressed"
            )
            continue

        candidate_total += len(candidate_chunks)
        candidate_lengths.extend(len(c) for c in candidate_chunks)

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
    print(f"Production boundaries:     {production_boundaries_total}")
    print(f"Accepted shifted bounds:   {len(accepted_shifts)}")
    print(
        f"Unchanged boundaries:      "
        f"{production_boundaries_total - len(accepted_shifts)}"
    )
    print(f"Sections with shifts:      {len(sections_shifted)}")

    if production_lengths and candidate_lengths:
        print()
        print("Chunk-size distribution")
        print("-" * 76)
        print(
            f"Production chars:          min={min(production_lengths):<5} "
            f"median={int(median(production_lengths)):<5} "
            f"max={max(production_lengths)}"
        )
        print(
            f"Candidate chars:           min={min(candidate_lengths):<5} "
            f"median={int(median(candidate_lengths)):<5} "
            f"max={max(candidate_lengths)}"
        )

    print()
    print("Candidate guards")
    print("-" * 76)
    print(f"No nearby safe boundary:   {boundaries_with_no_safe_legal_candidate}")
    print(f"Rejected by size guard:    {rejected_size}")
    print(f"Rejected by balance guard: {rejected_balance}")

    if invariant_errors:
        print()
        print("INVARIANT FAILURES")
        print("-" * 76)
        for error in invariant_errors:
            print(error)
        raise SystemExit("Constrained candidate rejected: invariant failure.")

    if candidate_total != expected_total:
        raise SystemExit(
            "Constrained candidate rejected: chunk-count invariant failed."
        )

    print()
    print("Chunk-count invariant:     PASS")
    print("MAX_CHARS invariant:       PASS")
    print("Balance guard:             PASS")

    if accepted_shifts:
        print()
        print("Accepted semantic boundary shifts")
        print("-" * 76)

        for shift in sorted(
            accepted_shifts,
            key=lambda item: (
                -item.semantic_distance,
                item.section_code,
                item.boundary_number,
            ),
        ):
            direction = "+" if shift.shift_chars > 0 else ""
            right = " ".join(shift.next_legal_block.split())
            if len(right) > 92:
                right = right[:89] + "..."

            print(
                f"{shift.section_code:<10} "
                f"boundary={shift.boundary_number:<2} "
                f"shift={direction}{shift.shift_chars:<5} "
                f"distance={shift.semantic_distance:.6f} "
                f"imbalance_delta={shift.imbalance_delta:+d}"
            )
            print(
                f"    production: "
                f"{shift.production_left_chars} / "
                f"{shift.production_right_chars} chars"
            )
            print(
                f"    candidate : "
                f"{shift.candidate_left_chars} / "
                f"{shift.candidate_right_chars} chars"
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
            "Test semantic relocation of existing production boundaries with "
            "hard size and chunk-balance guards."
        )
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--section")
    parser.add_argument(
        "--window",
        type=int,
        default=SHIFT_WINDOW_CHARS,
        help="Maximum source-character movement either side (default: 600).",
    )
    args = parser.parse_args()

    if not args.manifest.exists():
        parser.error(f"manifest not found: {args.manifest}")
    if args.window < 0:
        parser.error("--window must be zero or greater")

    asyncio.run(compare(args.manifest, args.section, args.window))


if __name__ == "__main__":
    main()