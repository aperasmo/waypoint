"""Read-only semantic chunking diagnostic for Waypoint.

Run from backend/:
    uv run python -m scripts.diagnose_semantic_chunking
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

import frontmatter

from app.ingestion.chunker import (
    MAX_CHARS,
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


@dataclass(frozen=True)
class SectionUnits:
    section_code: str
    title: str
    baseline_chunks: int
    units: list[str]


@dataclass(frozen=True)
class Boundary:
    section_code: str
    distance: float
    left_text: str
    right_text: str


def compact(text: str, limit: int = 90) -> str:
    value = " ".join(text.split())
    return value if len(value) <= limit else value[: limit - 3] + "..."


SECTION_HEADING_RE = re.compile(
    r"^[A-Z]{1,4}\d+(?:\.\d+)+(?:\.\d+)*\s+\S+"
)
ROOT_CLAUSE_RE = re.compile(r"^\([a-z0-9]+\)\s+", re.IGNORECASE)
LABEL_RE = re.compile(r"^(?:Note|Notes|Example|Examples):?$", re.IGNORECASE)


def starts_legal_block(line: str) -> bool:
    """Return True only for strong legal/structural boundaries."""
    stripped = line.strip()

    # Indented clauses such as (i), (ii), (iii) belong to their parent.
    if line[:1].isspace():
        return False

    return bool(
        ROOT_CLAUSE_RE.match(stripped)
        or SECTION_HEADING_RE.match(stripped)
        or LABEL_RE.match(stripped)
    )


def structural_units(text: str) -> list[str]:
    """Build coherent legal blocks for semantic-distance analysis.

    The scraper can emit inline links and punctuation on separate lines, e.g.
    "S6", ")" or "WI20". Treating each converted line as a semantic unit
    produces false topic shifts. This diagnostic therefore uses only strong
    legal boundaries:

    - top-level clauses such as (a), (b), (1), (2);
    - subsection headings such as SR5.5.1 Evidence;
    - Note / Example labels;
    - whole Markdown tables.

    Everything else is joined to the current block, including short policy
    references, punctuation fragments, and indented nested clauses.
    """
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

        # Keep a converted Markdown table intact.
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


def percentile(values: list[float], pct: float) -> float:
    if not values:
        raise ValueError("No distances available")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * (pct / 100.0)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def load_sections(
    manifest_path: Path,
    section_filter: str | None,
) -> tuple[list[SectionUnits], int, int]:
    baseline_chunks, _ = chunk_corpus(manifest_path)
    by_code: dict[str, list] = {}
    for chunk in baseline_chunks:
        by_code.setdefault(chunk.section_code, []).append(chunk)

    split_codes = {code for code, chunks in by_code.items() if len(chunks) > 1}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["pages"] if isinstance(manifest, dict) else manifest
    corpus_dir = manifest_path.parent
    sections: list[SectionUnits] = []

    for entry in entries:
        code = str(entry["section_code"])
        if code not in split_codes:
            continue
        if section_filter and code != section_filter:
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

        units = structural_units(body)
        if len(units) < 2:
            continue

        sections.append(
            SectionUnits(
                section_code=code,
                title=title,
                baseline_chunks=len(by_code[code]),
                units=units,
            )
        )

    return sections, len(baseline_chunks), len(split_codes)


async def diagnose(
    manifest_path: Path,
    section_filter: str | None,
    threshold_percentile: float,
    top_n: int,
) -> None:
    sections, corpus_chunk_count, split_section_count = load_sections(
        manifest_path, section_filter
    )

    if section_filter and not sections:
        raise SystemExit(
            f"{section_filter} is not currently split by the production "
            f"chunker (MAX_CHARS={MAX_CHARS}) or could not be loaded."
        )
    if not sections:
        raise SystemExit("No currently split sections were available.")

    embedder = OpenAIEmbedder()

    inputs: list[str] = []
    locations: list[tuple[str, int]] = []
    for section in sections:
        for index, unit in enumerate(section.units):
            inputs.append(f"{section.section_code}: {section.title}\n\n{unit}")
            locations.append((section.section_code, index))

    print("Waypoint semantic-chunking diagnostic")
    print("=" * 37)
    print(f"Manifest:                  {manifest_path}")
    print(f"Production MAX_CHARS:      {MAX_CHARS}")
    print(f"Production corpus chunks:  {corpus_chunk_count}")
    print(f"Production split sections: {split_section_count}")
    print(f"Sections analysed:         {len(sections)}")
    print(f"Split sections excluded:   {split_section_count - len(sections)}")
    print(f"Structural units:          {len(inputs)}")
    print(f"Embedding model:           {embedder.model_name}")
    print()
    print("Embedding structural units...")

    vectors = await embedder.embed_documents(inputs)
    if len(vectors) != len(inputs):
        raise RuntimeError(f"Expected {len(inputs)} embeddings, got {len(vectors)}")

    vector_by_location = dict(zip(locations, vectors, strict=True))
    boundaries: list[Boundary] = []

    for section in sections:
        for i in range(len(section.units) - 1):
            boundaries.append(
                Boundary(
                    section_code=section.section_code,
                    distance=cosine_distance(
                        vector_by_location[(section.section_code, i)],
                        vector_by_location[(section.section_code, i + 1)],
                    ),
                    left_text=section.units[i],
                    right_text=section.units[i + 1],
                )
            )

    distances = [b.distance for b in boundaries]
    threshold = percentile(distances, threshold_percentile)
    semantic_breaks = [b for b in boundaries if b.distance >= threshold]

    print()
    print(f"Adjacent boundaries:       {len(boundaries)}")
    print(f"{threshold_percentile:g}th pct threshold:       {threshold:.6f}")
    print(f"Candidate semantic breaks: {len(semantic_breaks)}")
    print()

    breaks_by_section: dict[str, int] = {}
    for boundary in semantic_breaks:
        breaks_by_section[boundary.section_code] = (
            breaks_by_section.get(boundary.section_code, 0) + 1
        )

    print("Per-section summary")
    print("-" * 72)
    for section in sections:
        print(
            f"{section.section_code:<10} "
            f"baseline_chunks={section.baseline_chunks:<3} "
            f"units={len(section.units):<3} "
            f"semantic_breaks={breaks_by_section.get(section.section_code, 0)}"
        )

    print()
    print(f"Top {min(top_n, len(boundaries))} semantic transitions")
    print("-" * 72)

    for rank, boundary in enumerate(
        sorted(boundaries, key=lambda b: b.distance, reverse=True)[:top_n],
        start=1,
    ):
        marker = "*" if boundary.distance >= threshold else " "
        print(
            f"{rank:>2}. {marker} {boundary.section_code:<10} "
            f"distance={boundary.distance:.6f}"
        )
        print(f"    left : {compact(boundary.left_text)}")
        print(f"    right: {compact(boundary.right_text)}")

    print()
    print("* = at or above the candidate semantic-break threshold")
    print("Read-only diagnostic complete. No corpus or database rows were changed.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Measure semantic transitions inside currently split Waypoint sections."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--section")
    parser.add_argument("--percentile", type=float, default=95.0)
    parser.add_argument("--top", type=int, default=20)
    args = parser.parse_args()

    if not 0.0 <= args.percentile <= 100.0:
        parser.error("--percentile must be between 0 and 100")
    if args.top <= 0:
        parser.error("--top must be greater than zero")
    if not args.manifest.exists():
        parser.error(f"manifest not found: {args.manifest}")

    asyncio.run(
        diagnose(
            manifest_path=args.manifest,
            section_filter=args.section,
            threshold_percentile=args.percentile,
            top_n=args.top,
        )
    )


if __name__ == "__main__":
    main()