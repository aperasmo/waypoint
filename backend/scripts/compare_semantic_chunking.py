"""Compare Waypoint's production chunking with a semantic-boundary candidate.

Read-only experiment. It does not modify the corpus, manifest, database, or
production chunker.

Candidate rule:
1. Keep every section <= MAX_CHARS unchanged.
2. For oversized sections, preserve coherent legal blocks first.
3. When a split is required, prefer the strongest semantic boundary among
   safe legal boundaries in the final 20% of the 3,000-character window.
4. If no semantic/legal boundary is usable, fall back to the production
   split_text() behaviour.
5. Keep the production 200-character overlap so the comparison changes only
   the boundary-selection strategy.

Run from backend/:
    uv run python -m scripts.compare_semantic_chunking
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
    split_text,
    strip_navigation,
)
from app.ingestion.embedder import OpenAIEmbedder


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
DEFAULT_MANIFEST = REPO_ROOT / "data" / "manifest.json"

# This is a boundary-selection window, not a semantic-score threshold.
# We only consider semantic boundaries after the candidate chunk has reached
# 80% of the same hard size ceiling used by production.
MIN_FILL_RATIO = 0.80

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
    baseline_count: int


@dataclass(frozen=True)
class CandidateResult:
    chunks: list[str]
    semantic_choices: int
    fallback_blocks: int


def starts_legal_block(line: str) -> bool:
    stripped = line.strip()
    if line[:1].isspace():
        return False
    return bool(
        ROOT_CLAUSE_RE.match(stripped)
        or SECTION_HEADING_RE.match(stripped)
        or LABEL_RE.match(stripped)
    )


def structural_units(text: str) -> list[str]:
    """Build coherent legal units, suppressing HTML-to-Markdown fragments."""
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    units: list[str] = []
    current: list[str] = []
    i = 0

    def flush() -> None:
        if current:
            units.append("\n".join(current).strip())
            current.clear()

    while i < len(lines):
        line = lines[i]

        if line.lstrip().startswith("|"):
            flush()
            table_lines = [line]
            i += 1
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            units.append("\n".join(table_lines).strip())
            continue

        if starts_legal_block(line):
            flush()

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


def join_units(units: list[str], start: int, end: int) -> str:
    return "\n".join(units[start:end]).strip()


def load_sections(manifest_path: Path) -> tuple[list[SectionBody], int]:
    baseline_chunks, _ = chunk_corpus(manifest_path)
    by_code: dict[str, list] = {}
    for chunk in baseline_chunks:
        by_code.setdefault(chunk.section_code, []).append(chunk)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["pages"] if isinstance(manifest, dict) else manifest
    corpus_dir = manifest_path.parent

    sections: list[SectionBody] = []
    for entry in entries:
        code = str(entry["section_code"])
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
                baseline_count=len(by_code.get(code, [])),
            )
        )

    return sections, len(baseline_chunks)


def build_boundaries(
    section: SectionBody,
    units: list[str],
    vectors: dict[tuple[str, int], list[float]],
) -> dict[int, float]:
    """Map boundary index -> cosine distance.

    Boundary i is the split between units i-1 and i.
    """
    distances: dict[int, float] = {}
    for i in range(1, len(units)):
        distances[i] = cosine_distance(
            vectors[(section.section_code, i - 1)],
            vectors[(section.section_code, i)],
        )
    return distances


def candidate_chunks(
    text: str,
    units: list[str],
    boundary_distances: dict[int, float],
    max_chars: int = MAX_CHARS,
    overlap: int = OVERLAP_CHARS,
    min_fill_ratio: float = MIN_FILL_RATIO,
) -> CandidateResult:
    """Split using semantic ranking only when a size split is already required."""
    if len(text) <= max_chars:
        return CandidateResult([text], 0, 0)

    if len(units) < 2:
        return CandidateResult(split_text(text, max_chars, overlap), 0, 1)

    chunks: list[str] = []
    semantic_choices = 0
    fallback_blocks = 0
    start = 0
    overlap_prefix = ""

    while start < len(units):
        # If one coherent legal unit is itself oversized, preserve our
        # production fallback rather than inventing a semantic boundary.
        if len(units[start]) > max_chars:
            fallback = split_text(units[start], max_chars, overlap)
            if overlap_prefix and fallback:
                fallback[0] = f"{overlap_prefix}\n{fallback[0]}"
            chunks.extend(fallback)
            fallback_blocks += 1
            overlap_prefix = fallback[-1][-overlap:] if overlap and fallback else ""
            start += 1
            continue

        # Find every whole-unit boundary that fits under the hard ceiling,
        # accounting for the same overlap prefix used by production.
        fitting_ends: list[int] = []
        end = start + 1
        while end <= len(units):
            body = join_units(units, start, end)
            candidate = f"{overlap_prefix}\n{body}" if overlap_prefix else body
            if len(candidate) > max_chars:
                break
            fitting_ends.append(end)
            end += 1

        if not fitting_ends:
            # Defensive fallback. This should only occur through unusual
            # overlap interactions.
            fallback = split_text(units[start], max_chars, overlap)
            if overlap_prefix and fallback:
                fallback[0] = f"{overlap_prefix}\n{fallback[0]}"
            chunks.extend(fallback)
            fallback_blocks += 1
            overlap_prefix = fallback[-1][-overlap:] if overlap and fallback else ""
            start += 1
            continue

        furthest = fitting_ends[-1]

        # If the rest fits, finish without creating a gratuitous semantic split.
        if furthest == len(units):
            body = join_units(units, start, furthest)
            final = f"{overlap_prefix}\n{body}" if overlap_prefix else body
            chunks.append(final)
            break

        # Consider only boundaries in the final 20% of the size window.
        eligible: list[tuple[float, int, int]] = []
        min_chars = int(max_chars * min_fill_ratio)

        for boundary in fitting_ends:
            if boundary >= len(units):
                continue
            body = join_units(units, start, boundary)
            candidate = f"{overlap_prefix}\n{body}" if overlap_prefix else body
            if len(candidate) < min_chars:
                continue
            distance = boundary_distances.get(boundary)
            if distance is not None:
                eligible.append((distance, len(candidate), boundary))

        if eligible:
            # Strongest semantic transition wins. Size is the deterministic
            # tie-breaker, favouring the fuller chunk.
            _, _, chosen_end = max(eligible, key=lambda item: (item[0], item[1]))
            semantic_choices += 1
        else:
            # No safe semantic boundary in the preferred window. Use the
            # furthest legal boundary under MAX_CHARS.
            chosen_end = furthest

        body = join_units(units, start, chosen_end)
        chunk = f"{overlap_prefix}\n{body}" if overlap_prefix else body
        chunks.append(chunk)
        overlap_prefix = chunk[-overlap:] if overlap else ""
        start = chosen_end

    return CandidateResult(chunks, semantic_choices, fallback_blocks)


async def compare(
    manifest_path: Path,
    section_filter: str | None,
) -> None:
    sections, baseline_total = load_sections(manifest_path)

    if section_filter:
        sections = [s for s in sections if s.section_code == section_filter]
        if not sections:
            raise SystemExit(f"Section not found: {section_filter}")

    oversized = [s for s in sections if len(s.body) > MAX_CHARS]

    units_by_code: dict[str, list[str]] = {}
    inputs: list[str] = []
    locations: list[tuple[str, int]] = []

    for section in oversized:
        units = structural_units(section.body)
        units_by_code[section.section_code] = units

        if len(units) < 2:
            continue

        for index, unit in enumerate(units):
            inputs.append(f"{section.section_code}: {section.title}\n\n{unit}")
            locations.append((section.section_code, index))

    embedder = OpenAIEmbedder()

    print("Waypoint chunking A/B pre-evaluation")
    print("=" * 36)
    print(f"Manifest:                  {manifest_path}")
    print(f"Production MAX_CHARS:      {MAX_CHARS}")
    print(f"Production overlap:        {OVERLAP_CHARS}")
    print(f"Semantic choice window:    {int(MIN_FILL_RATIO * 100)}%-100% of MAX_CHARS")
    print(f"Sections inspected:        {len(sections)}")
    print(f"Oversized sections:        {len(oversized)}")
    print(f"Semantic analysis units:   {len(inputs)}")
    print(f"Embedding model:           {embedder.model_name}")

    vectors_by_location: dict[tuple[str, int], list[float]] = {}
    if inputs:
        print()
        print("Embedding legal units...")
        vectors = await embedder.embed_documents(inputs)
        if len(vectors) != len(inputs):
            raise RuntimeError(f"Expected {len(inputs)} embeddings, got {len(vectors)}")
        vectors_by_location = dict(zip(locations, vectors, strict=True))

    candidate_total = 0
    changed_count = 0
    semantic_choice_total = 0
    fallback_total = 0
    changed_rows: list[tuple[str, int, int, int, int, int]] = []
    candidate_lengths: list[int] = []

    for section in sections:
        if len(section.body) <= MAX_CHARS:
            result = CandidateResult([section.body], 0, 0)
        else:
            units = units_by_code[section.section_code]
            distances = (
                build_boundaries(section, units, vectors_by_location)
                if len(units) >= 2
                else {}
            )
            result = candidate_chunks(section.body, units, distances)

        candidate_total += len(result.chunks)
        semantic_choice_total += result.semantic_choices
        fallback_total += result.fallback_blocks
        candidate_lengths.extend(len(chunk) for chunk in result.chunks)

        if len(result.chunks) != section.baseline_count:
            changed_count += 1
            changed_rows.append(
                (
                    section.section_code,
                    len(section.body),
                    section.baseline_count,
                    len(result.chunks),
                    result.semantic_choices,
                    result.fallback_blocks,
                )
            )

    if section_filter:
        baseline_display = sum(s.baseline_count for s in sections)
    else:
        baseline_display = baseline_total

    print()
    print("Summary")
    print("-" * 72)
    print(f"Production chunks:         {baseline_display}")
    print(f"Candidate chunks:          {candidate_total}")
    print(f"Chunk-count delta:         {candidate_total - baseline_display:+d}")
    print(f"Sections count-changed:    {changed_count}")
    print(f"Semantic split choices:    {semantic_choice_total}")
    print(f"Fallback oversized blocks: {fallback_total}")

    if candidate_lengths:
        print(f"Candidate min chars:       {min(candidate_lengths)}")
        print(f"Candidate median chars:    {int(median(candidate_lengths))}")
        print(f"Candidate max chars:       {max(candidate_lengths)}")

    if changed_rows:
        print()
        print("Sections with changed chunk counts")
        print("-" * 72)
        for code, chars, baseline, candidate, choices, fallbacks in changed_rows:
            print(
                f"{code:<10} chars={chars:<6} "
                f"baseline={baseline:<2} candidate={candidate:<2} "
                f"semantic_choices={choices:<2} fallbacks={fallbacks}"
            )

    print()
    print("Read-only comparison complete. No corpus or database rows were changed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare production chunking with a semantic-boundary candidate."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--section")
    args = parser.parse_args()

    if not args.manifest.exists():
        parser.error(f"manifest not found: {args.manifest}")

    asyncio.run(compare(args.manifest, args.section))


if __name__ == "__main__":
    main()