"""
Audit the rebuilt Waypoint staging corpus against its manually archived MHTML
sources.

READ ONLY.

Validates the provenance chain:

MHTML archive
    -> validated current policy HTML
    -> extracted policy text
    -> staging Markdown
    -> staging manifest

No active corpus, manifest, database, embeddings, or frontend files are
modified.
"""

from __future__ import annotations

import json
import sys
import traceback
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

import frontmatter

try:
    from .build_staging_corpus import normalise_source_url
    from .manual_extract import content_hash, extract_content
    from .mhtml_ingest import extract_policy_html_from_mhtml
except ImportError:
    from build_staging_corpus import normalise_source_url
    from manual_extract import content_hash, extract_content
    from mhtml_ingest import extract_policy_html_from_mhtml


PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = PROJECT_ROOT / "data"

STAGING_DIR = DATA_DIR / "staging"

MANIFEST_PATH = STAGING_DIR / "manifest.json"

ARCHIVE_DIR = (
    DATA_DIR
    / "source_archive"
    / "operational_manual"
)


def _relative_path(value: str) -> Path:
    """Convert manifest-style path separators into a local Path."""
    return Path(
        value.replace("\\", "/")
    )


def _resolve_archive_path(value: str) -> Path:
    """Resolve a provenance path relative to data/ when necessary."""
    path = _relative_path(value)

    if path.is_absolute():
        return path

    return DATA_DIR / path


def main() -> int:
    """Validate staging provenance without modifying any project data."""
    try:
        print("[START] Auditing Waypoint staging integrity")
        print("[INFO] READ ONLY")
        print(f"[INFO] Manifest: {MANIFEST_PATH}")
        print(f"[INFO] Archive:  {ARCHIVE_DIR}")

        if not MANIFEST_PATH.exists():
            raise FileNotFoundError(
                f"Staging manifest not found: {MANIFEST_PATH}"
            )

        manifest = json.loads(
            MANIFEST_PATH.read_text(
                encoding="utf-8"
            )
        )

        if not isinstance(manifest, dict):
            raise ValueError(
                "Staging manifest root must be an object."
            )

        entries = manifest.get("pages")

        if not isinstance(entries, list):
            raise ValueError(
                "Staging manifest does not contain a pages list."
            )

        archive_files = sorted(
            ARCHIVE_DIR.glob("*.mhtml")
        )

        markdown_files = sorted(
            STAGING_DIR.rglob("*.md")
        )

        errors: list[str] = []

        manifest_codes = [
            str(entry.get("section_code", "")).strip()
            for entry in entries
        ]

        archive_codes = {
            path.stem
            for path in archive_files
        }

        manifest_code_set = set(
            manifest_codes
        )

        duplicate_codes = sorted(
            code
            for code, count in Counter(
                manifest_codes
            ).items()
            if code and count > 1
        )

        if duplicate_codes:
            errors.append(
                "Duplicate manifest section codes: "
                + ", ".join(duplicate_codes)
            )

        missing_from_manifest = sorted(
            archive_codes - manifest_code_set
        )

        missing_from_archive = sorted(
            manifest_code_set - archive_codes
        )

        if missing_from_manifest:
            errors.append(
                "Archived MHTML missing from manifest: "
                + ", ".join(missing_from_manifest)
            )

        if missing_from_archive:
            errors.append(
                "Manifest sections missing MHTML source: "
                + ", ".join(missing_from_archive)
            )

        manifest_files: set[str] = set()

        for entry in entries:
            file_value = entry.get("file")

            if isinstance(file_value, str):
                manifest_files.add(
                    _relative_path(
                        file_value
                    ).as_posix()
                )

        actual_markdown_files = {
            path.relative_to(
                STAGING_DIR
            ).as_posix()
            for path in markdown_files
        }

        orphan_markdown = sorted(
            actual_markdown_files
            - manifest_files
        )

        missing_markdown = sorted(
            manifest_files
            - actual_markdown_files
        )

        if orphan_markdown:
            errors.append(
                "Markdown files not listed in manifest: "
                + ", ".join(orphan_markdown)
            )

        if missing_markdown:
            errors.append(
                "Manifest Markdown files missing on disk: "
                + ", ".join(missing_markdown)
            )

        source_urls: list[str] = []

        verified = 0

        for index, entry in enumerate(
            entries,
            start=1,
        ):
            code = str(
                entry.get(
                    "section_code",
                    "",
                )
            ).strip()

            print(
                f"[{index:03d}/{len(entries):03d}] "
                f"{code or '<missing code>'}"
            )

            required_fields = (
                "section_code",
                "title",
                "file",
                "source_url",
                "effective_date",
                "content_hash",
                "source_archive_file",
            )

            missing_fields = [
                field
                for field in required_fields
                if field not in entry
            ]

            if missing_fields:
                errors.append(
                    f"{code}: missing manifest fields: "
                    + ", ".join(missing_fields)
                )
                continue

            if not code:
                errors.append(
                    "Manifest entry has an empty section_code."
                )
                continue

            file_value = str(
                entry["file"]
            )

            markdown_path = (
                STAGING_DIR
                / _relative_path(file_value)
            )

            if not markdown_path.exists():
                errors.append(
                    f"{code}: Markdown file missing: "
                    f"{markdown_path}"
                )
                continue

            if markdown_path.stem != code:
                errors.append(
                    f"{code}: Markdown filename does not "
                    f"match section code: {markdown_path.name}"
                )

            archive_value = str(
                entry["source_archive_file"]
            )

            archive_path = _resolve_archive_path(
                archive_value
            )

            if not archive_path.exists():
                errors.append(
                    f"{code}: archived source missing: "
                    f"{archive_path}"
                )
                continue

            if archive_path.name != f"{code}.mhtml":
                errors.append(
                    f"{code}: archive filename mismatch: "
                    f"{archive_path.name}"
                )

            post = frontmatter.load(
                markdown_path
            )

            metadata_checks = {
                "section_code": code,
                "title": entry.get("title"),
                "source_url": entry.get("source_url"),
                "effective_date": entry.get(
                    "effective_date"
                ),
                "source_archive_file": entry.get(
                    "source_archive_file"
                ),
            }

            for field, expected in metadata_checks.items():
                actual = post.get(field)

                if actual != expected:
                    errors.append(
                        f"{code}: frontmatter {field} mismatch "
                        f"(manifest={expected!r}, "
                        f"markdown={actual!r})"
                    )

            html, content_location, heading = (
                extract_policy_html_from_mhtml(
                    archive_path
                )
            )

            extracted = extract_content(
                html
            )

            if heading != entry.get("title"):
                errors.append(
                    f"{code}: MHTML heading/title mismatch "
                    f"(heading={heading!r}, "
                    f"manifest={entry.get('title')!r})"
                )

            if content_location is None:
                errors.append(
                    f"{code}: MHTML Content-Location missing"
                )
            else:
                expected_source_url = (
                    normalise_source_url(
                        content_location
                    )
                )

                if (
                    expected_source_url
                    != entry.get("source_url")
                ):
                    errors.append(
                        f"{code}: source URL mismatch "
                        f"(MHTML={expected_source_url!r}, "
                        f"manifest={entry.get('source_url')!r})"
                    )

            source_url = str(
                entry.get(
                    "source_url",
                    "",
                )
            )

            source_urls.append(
                source_url
            )

            parsed_url = urlparse(
                source_url
            )

            if (
                parsed_url.scheme != "https"
                or parsed_url.netloc
                != "www.immigration.govt.nz"
                or not parsed_url.path.startswith(
                    "/opsmanual/"
                )
            ):
                errors.append(
                    f"{code}: unexpected source URL: "
                    f"{source_url}"
                )

            if parsed_url.fragment:
                errors.append(
                    f"{code}: source URL still contains "
                    f"a fragment: {source_url}"
                )

            extracted_date = extracted[
                "effective_date"
            ]

            if (
                extracted_date
                != entry.get("effective_date")
            ):
                errors.append(
                    f"{code}: effective date mismatch "
                    f"(extracted={extracted_date!r}, "
                    f"manifest="
                    f"{entry.get('effective_date')!r})"
                )

            expected_hash = entry.get(
                "content_hash"
            )

            extracted_hash = content_hash(
                extracted["text"]
            )

            markdown_hash = content_hash(
                post.content
            )

            if extracted_hash != expected_hash:
                errors.append(
                    f"{code}: extracted MHTML hash mismatch "
                    f"(extracted={extracted_hash}, "
                    f"manifest={expected_hash})"
                )

            if markdown_hash != expected_hash:
                errors.append(
                    f"{code}: Markdown body hash mismatch "
                    f"(markdown={markdown_hash}, "
                    f"manifest={expected_hash})"
                )

            if (
                extracted["policy_tables"]
                != extracted["converted_tables"]
            ):
                errors.append(
                    f"{code}: table conversion mismatch "
                    f"{extracted['policy_tables']}/"
                    f"{extracted['converted_tables']}"
                )

            if (
                extracted["policy_lists"]
                != extracted["converted_lists"]
            ):
                errors.append(
                    f"{code}: list conversion mismatch "
                    f"{extracted['policy_lists']}/"
                    f"{extracted['converted_lists']}"
                )

            verified += 1

        duplicate_urls = sorted(
            url
            for url, count in Counter(
                source_urls
            ).items()
            if url and count > 1
        )

        if duplicate_urls:
            errors.append(
                "Duplicate source URLs: "
                + ", ".join(duplicate_urls)
            )

        print()
        print("Staging integrity audit")
        print("-----------------------")
        print(
            f"MHTML files:          {len(archive_files)}"
        )
        print(
            f"Manifest entries:     {len(entries)}"
        )
        print(
            f"Markdown files:       {len(markdown_files)}"
        )
        print(
            f"Sections verified:    {verified}"
        )
        print(
            f"Duplicate codes:      {len(duplicate_codes)}"
        )
        print(
            f"Orphan Markdown:      {len(orphan_markdown)}"
        )
        print(
            f"Missing Markdown:     {len(missing_markdown)}"
        )
        print(
            f"Integrity errors:     {len(errors)}"
        )

        if errors:
            print()
            print("[FAILURES]")

            for error in errors:
                print(
                    f"  - {error}"
                )

            return 2

        print()
        print(
            "[OK] MHTML, Markdown, and manifest "
            "provenance are internally consistent."
        )
        print(
            "[OK] Every staging section traces back "
            "to its archived INZ MHTML source."
        )
        print(
            "[OK] No files were modified."
        )

        return 0

    except Exception as exc:
        print(
            f"[ERROR] Staging integrity audit failed: "
            f"{exc}"
        )
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(
        main()
    )