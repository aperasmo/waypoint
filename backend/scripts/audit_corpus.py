"""Read-only audit of the current Waypoint corpus.

Location:
    waypoint/backend/scripts/audit_corpus.py

Run from backend/:
    .venv\\Scripts\\python.exe scripts\\audit_corpus.py

This script does not import the Waypoint app, Settings, database, OpenAI,
or third-party packages. It follows the current project layout directly:
backend/app and backend/scripts are siblings, while data/ is beside backend/.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

# backend/scripts/audit_corpus.py -> scripts -> backend -> waypoint
SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = REPO_ROOT / "data"

MANIFEST_PATH = DATA_DIR / "manifest.json"
CATEGORIES_PATH = DATA_DIR / "categories.json"

# Keep these aligned with backend/app/ingestion/chunker.py.
MAX_CHARS = 3000
OVERLAP_CHARS = 200
NAV_MARKERS = frozenset(
    {
        "in this section",
        "previous immigration instructions",
        "top",
        "print this page",
    }
)
EFFECTIVE_LINE = re.compile(r"^effective\s+\d{2}/\d{2}/\d{4}$", re.IGNORECASE)


def parse_front_matter(md_text: str) -> tuple[dict[str, object], str]:
    """Read the simple front matter format produced by the Waypoint scraper."""
    if not md_text.startswith("---"):
        return {}, md_text

    end = md_text.find("\n---", 3)
    if end == -1:
        return {}, md_text

    block = md_text[3:end].strip()
    body = md_text[end + 4 :].lstrip("\r\n")
    metadata: dict[str, object] = {}

    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, raw_value = line.partition(":")
        raw_value = raw_value.strip()
        try:
            value: object = json.loads(raw_value)
        except json.JSONDecodeError:
            value = raw_value
        metadata[key.strip()] = value

    return metadata, body


def strip_navigation(body: str) -> str:
    """Mirror the current chunker's navigation stripping."""
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
    """Mirror backend/app/ingestion/chunker.py normalisation."""
    text = text.replace("\r\n", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+$", "", text, flags=re.MULTILINE)
    return text.strip()


def drop_repeated_title(body: str, title: str) -> str:
    lines = body.splitlines()
    if lines and lines[0].strip() == title.strip():
        return "\n".join(lines[1:]).strip()
    return body


def split_text(
    text: str,
    max_chars: int = MAX_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> list[str]:
    """Mirror the current chunker's splitting behaviour."""
    if len(text) <= max_chars:
        return [text]

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


def source_content_hash(body: str) -> str:
    """Mirror scraper/check_for_updates.py content_hash()."""
    normalized = re.sub(r"\s+", " ", body).strip()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]


def matches(section_code: str, prefixes: list[str]) -> bool:
    """Mirror backend/app/api/routes/browse.py prefix matching."""
    for prefix in prefixes:
        if section_code == prefix or section_code.startswith(f"{prefix}."):
            return True
    return False


def main() -> None:
    print("Waypoint corpus audit")
    print("=" * 22)
    print(f"Repository root: {REPO_ROOT}")
    print(f"Data directory:  {DATA_DIR}")
    print()

    if not MANIFEST_PATH.exists():
        raise SystemExit(f"ERROR: manifest not found: {MANIFEST_PATH}")
    if not CATEGORIES_PATH.exists():
        raise SystemExit(f"ERROR: categories file not found: {CATEGORIES_PATH}")

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entries = manifest.get("pages", []) if isinstance(manifest, dict) else manifest
    taxonomy = json.loads(CATEGORIES_PATH.read_text(encoding="utf-8"))

    manifest_codes: list[str] = []
    manifest_files: set[Path] = set()
    duplicate_codes: list[str] = []
    seen_codes: set[str] = set()
    missing_files: list[str] = []
    hash_mismatches: list[str] = []
    dates_unparsed: list[str] = []
    empty_sections: list[str] = []
    split_sections: list[str] = []
    substantive_codes: list[str] = []

    files_read = 0
    chunk_count = 0

    for entry in entries:
        code = str(entry["section_code"])
        manifest_codes.append(code)
        if code in seen_codes:
            duplicate_codes.append(code)
        seen_codes.add(code)

        relative = Path(str(entry["file"]).replace("\\", "/"))
        manifest_files.add(relative)
        path = DATA_DIR / relative

        if not path.exists():
            missing_files.append(code)
            continue

        files_read += 1
        md_text = path.read_text(encoding="utf-8")
        metadata, raw_body = parse_front_matter(md_text)

        expected_hash = entry.get("content_hash")
        if expected_hash:
            actual_hash = source_content_hash(raw_body)
            if actual_hash != expected_hash:
                hash_mismatches.append(code)

        raw_date = entry.get("effective_date")
        if raw_date:
            try:
                datetime.strptime(str(raw_date).strip(), "%d/%m/%Y")
            except ValueError:
                dates_unparsed.append(code)

        title = str(metadata.get("title") or entry.get("title") or code)
        body = strip_navigation(raw_body)
        body = drop_repeated_title(body, title)
        body = normalise(body)

        if not body:
            empty_sections.append(code)
            continue

        pieces = split_text(body)
        substantive_codes.append(code)
        chunk_count += len(pieces)
        if len(pieces) > 1:
            split_sections.append(code)

    markdown_files = {
        p.relative_to(DATA_DIR)
        for p in DATA_DIR.rglob("*.md")
        if p.is_file()
    }
    unreferenced_markdown = sorted(
        markdown_files - manifest_files,
        key=lambda p: p.as_posix().lower(),
    )

    branch_prefixes = [
        prefix
        for group in taxonomy.get("groups", [])
        for branch in group.get("branches", [])
        for prefix in branch.get("prefixes", [])
    ]
    browse_unmapped = sorted(
        code
        for code in substantive_codes
        if not matches(code, branch_prefixes)
    )

    print(f"Manifest entries:       {len(entries)}")
    print(f"Unique section codes:   {len(seen_codes)}")
    print(f"Files read:             {files_read}")
    print(f"Substantive sections:   {len(substantive_codes)}")
    print(f"Generated chunks:       {chunk_count}")
    print(f"Empty/index sections:   {len(empty_sections)}")
    print(f"Split sections:         {len(split_sections)}")
    print()

    print(f"Missing files:          {missing_files or 'none'}")
    print(f"Duplicate codes:        {duplicate_codes or 'none'}")
    print(f"Hash mismatches:        {hash_mismatches or 'none'}")
    print(f"Unparsed dates:         {dates_unparsed or 'none'}")
    print(f"Unreferenced markdown:  {len(unreferenced_markdown)}")
    for path in unreferenced_markdown:
        print(f"  - {path.as_posix()}")
    print(f"Browse-unmapped:        {browse_unmapped or 'none'}")

    print()
    if missing_files or duplicate_codes or hash_mismatches or dates_unparsed or browse_unmapped:
        print("Audit result: ATTENTION REQUIRED")
    else:
        print("Audit result: OK")

    print("Read-only audit complete. No files or database rows were changed.")


if __name__ == "__main__":
    main()