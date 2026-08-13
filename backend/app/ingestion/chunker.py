"""Turn corpus markdown files into chunks ready for embedding.

Pure functions over the filesystem. No database, no network, no embeddings.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import frontmatter

MAX_CHARS = 3000
OVERLAP_CHARS = 200

# Website furniture that follows the policy text. Matched against a whole
# stripped line, so a mid-sentence mention of similar wording is left alone.
NAV_MARKERS = frozenset(
    {
        "in this section",
        "previous immigration instructions",
        "top",
        "print this page",
    }
)

EFFECTIVE_LINE = re.compile(r"^effective\s+\d{2}/\d{2}/\d{4}$", re.IGNORECASE)


@dataclass(frozen=True)
class Chunk:
    section_code: str
    title: str
    source_url: str
    effective_date: str | None
    content_hash: str | None
    chunk_index: int
    chunk_total: int
    text: str

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass
class ChunkReport:
    """What happened during a run. Kept separate from the chunks themselves
    so ingestion can log it without polluting the data."""

    files_read: int = 0
    files_skipped_empty: list[str] = field(default_factory=list)
    files_missing: list[str] = field(default_factory=list)
    files_split: list[str] = field(default_factory=list)
    chars_stripped: dict[str, int] = field(default_factory=dict)


def strip_navigation(body: str) -> str:
    """Drop the trailing website furniture and the duplicated effective line.

    Everything from the first navigation marker onward is removed. The marker
    must be the entire line, so 'see the requirements in this section below'
    inside real policy text will not trigger it.
    """
    kept: list[str] = []

    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.lower() in NAV_MARKERS:
            break
        if EFFECTIVE_LINE.match(line):
            continue
        kept.append(raw_line)

    return "\n".join(kept).strip()


def normalise(text: str) -> str:
    """Collapse the ragged blank lines left by the HTML conversion."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    return text.strip()


def drop_repeated_title(body: str, title: str) -> str:
    """The first body line repeats the front-matter title in every file."""
    lines = body.splitlines()
    if lines and lines[0].strip() == title.strip():
        return "\n".join(lines[1:]).strip()
    return body


def split_text(text: str, max_chars: int = MAX_CHARS, overlap: int = OVERLAP_CHARS) -> list[str]:
    """Split on paragraph boundaries, never mid-sentence.

    A single paragraph longer than max_chars is left oversized rather than
    cut arbitrarily. Losing the boundary matters more than the size limit.
    """
    if len(text) <= max_chars:
        return [text]

    # The HTML conversion emits one line per element and no blank lines, so
    # a line is the only boundary available. Blank-line splitting was tried
    # first and silently never fired.
    paragraphs = [p for p in text.split("\n") if p.strip()]
    pieces: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n{para}" if current else para
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            pieces.append(current)
            tail = current[-overlap:] if overlap else ""
            current = f"{tail}\n{para}" if tail else para
        else:
            current = para

    if current:
        pieces.append(current)

    return pieces


def chunk_file(path: Path, entry: dict, report: ChunkReport) -> list[Chunk]:
    post = frontmatter.load(path)
    title = str(post.get("title") or entry.get("title") or entry["section_code"])

    original_len = len(post.content)
    body = strip_navigation(post.content)
    body = drop_repeated_title(body, title)
    body = normalise(body)

    report.chars_stripped[entry["section_code"]] = original_len - len(body)

    if not body:
        report.files_skipped_empty.append(entry["section_code"])
        return []

    pieces = split_text(body)
    if len(pieces) > 1:
        report.files_split.append(entry["section_code"])

    return [
        Chunk(
            section_code=entry["section_code"],
            title=title,
            source_url=entry.get("source_url", ""),
            effective_date=entry.get("effective_date"),
            content_hash=entry.get("content_hash"),
            chunk_index=i,
            chunk_total=len(pieces),
            text=piece,
        )
        for i, piece in enumerate(pieces)
    ]


def chunk_corpus(manifest_path: Path) -> tuple[list[Chunk], ChunkReport]:
    """Read every section listed in the manifest and return its chunks.

    The manifest is the source of truth, not a directory walk. Files on disk
    that the manifest does not list are deliberately ignored.
    """
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    entries = manifest["pages"] if isinstance(manifest, dict) else manifest
    corpus_dir = manifest_path.parent

    report = ChunkReport()
    chunks: list[Chunk] = []

    for entry in entries:
        path = corpus_dir / Path(entry["file"].replace("\\", "/"))
        if not path.exists():
            report.files_missing.append(entry["section_code"])
            continue

        report.files_read += 1
        chunks.extend(chunk_file(path, entry, report))

    return chunks, report