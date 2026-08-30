"""
build_staging_corpus.py

Build a complete Waypoint corpus staging area from manually archived INZ
Operational Manual MHTML files.

Pipeline:
    validated MHTML
        -> policy HTML
        -> manual_extract.py
        -> Markdown
        -> staging manifest

This script performs no network access and never modifies the active corpus,
active manifest, database, chunks, or embeddings.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

try:
    # Package-style import, e.g. `from scripts.build_staging_corpus import ...`
    from .manual_extract import content_hash, extract_content
    from .mhtml_ingest import extract_policy_html_from_mhtml

except ImportError:
    # Direct script execution, e.g. `python scripts\build_staging_corpus.py`
    from manual_extract import content_hash, extract_content
    from mhtml_ingest import extract_policy_html_from_mhtml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"

ARCHIVE_DIR = (
    DATA_DIR
    / "source_archive"
    / "operational_manual"
)

STAGING_DIR = DATA_DIR / "staging"
CORPUS_SUBDIR = "operational_manual"


def normalise_source_url(content_location: str | None) -> str:
    """Convert an archived INZ Content-Location into its direct page URL.

    Chrome saves rendered Operational Manual pages using a fragment form such
    as /opsmanual/#46189.htm. If the fragment represents the page resource,
    move it into the URL path. Other URLs are returned unchanged.
    """
    try:
        if not content_location:
            raise ValueError("MHTML Content-Location is missing.")

        parsed = urlsplit(content_location)

        fragment = parsed.fragment.strip()
        path = parsed.path.rstrip("/")

        if fragment and fragment.lower().endswith(".htm"):
            path = f"{path}/{fragment}"

            return urlunsplit(
                (
                    parsed.scheme,
                    parsed.netloc,
                    path,
                    parsed.query,
                    "",
                )
            )

        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.query,
                "",
            )
        )

    except Exception as exc:
        print(
            f"[ERROR] Failed to normalise source URL "
            f"{content_location!r}: {exc}"
        )
        traceback.print_exc()
        raise


def derive_manual_toc_url(source_url: str) -> str:
    """Derive the Operational Manual TOC URL from a parsed source URL."""
    try:
        parsed = urlsplit(source_url)

        parent_path = str(Path(parsed.path).parent).replace("\\", "/")
        toc_path = f"{parent_path.rstrip('/')}/toc.htm"

        return urlunsplit(
            (
                parsed.scheme,
                parsed.netloc,
                toc_path,
                "",
                "",
            )
        )

    except Exception as exc:
        print(
            f"[ERROR] Failed to derive manual TOC URL from "
            f"{source_url}: {exc}"
        )
        traceback.print_exc()
        raise


def write_markdown(
    file_path: Path,
    section_code: str,
    title: str,
    source_url: str,
    effective_date: str | None,
    archive_file: str,
    text: str,
) -> None:
    """Write one staged Markdown section using the existing corpus contract."""
    try:
        front_matter = {
            "section_code": section_code,
            "title": title,
            "source_url": source_url,
            "effective_date": effective_date,
            "source_archive_file": archive_file,
        }

        front_matter_lines = "\n".join(
            f"{key}: {json.dumps(value, ensure_ascii=False)}"
            for key, value in front_matter.items()
        )

        file_path.parent.mkdir(parents=True, exist_ok=True)

        file_path.write_text(
            f"---\n"
            f"{front_matter_lines}\n"
            f"---\n\n"
            f"{text}\n",
            encoding="utf-8",
        )

    except Exception as exc:
        print(f"[ERROR] Failed writing {file_path}: {exc}")
        traceback.print_exc()
        raise


def build_section(
    mhtml_path: Path,
    output_root: Path,
) -> dict[str, object]:
    """Parse, validate, and stage one archived Operational Manual section."""
    try:
        section_code = mhtml_path.stem

        print(f"[START] Building {section_code}")

        policy_html, content_location, heading = (
            extract_policy_html_from_mhtml(mhtml_path)
        )

        source_url = normalise_source_url(content_location)
        parsed = extract_content(policy_html)

        text = str(parsed["text"]).strip()
        effective_date = parsed["effective_date"]

        if not text:
            raise ValueError(
                f"{section_code}: extracted policy text is empty."
            )

        if not text.casefold().startswith(heading.casefold()):
            raise ValueError(
                f"{section_code}: extracted body does not begin "
                "with the validated instruction heading."
            )

        policy_tables = int(parsed["policy_tables"])
        converted_tables = int(parsed["converted_tables"])

        if policy_tables != converted_tables:
            raise ValueError(
                f"{section_code}: table conversion mismatch "
                f"{policy_tables}/{converted_tables}."
            )

        policy_lists = int(parsed["policy_lists"])
        converted_lists = int(parsed["converted_lists"])

        if policy_lists != converted_lists:
            raise ValueError(
                f"{section_code}: list conversion mismatch "
                f"{policy_lists}/{converted_lists}."
            )

        body_hash = content_hash(text)

        archive_relative = mhtml_path.relative_to(DATA_DIR)
        archive_file = str(archive_relative).replace("/", "\\")

        markdown_relative = (
            Path(CORPUS_SUBDIR)
            / f"{section_code}.md"
        )

        markdown_path = output_root / markdown_relative

        write_markdown(
            file_path=markdown_path,
            section_code=section_code,
            title=heading,
            source_url=source_url,
            effective_date=effective_date,
            archive_file=archive_file,
            text=text,
        )

        manifest_file = str(markdown_relative).replace("/", "\\")

        print(
            f"[OK] {section_code} "
            f"| chars={len(text)} "
            f"| date={effective_date or 'N/A'} "
            f"| tables={policy_tables}/{converted_tables} "
            f"| lists={policy_lists}/{converted_lists}"
        )

        return {
            "section_code": section_code,
            "title": heading,
            "file": manifest_file,
            "source_url": source_url,
            "effective_date": effective_date,
            "content_hash": body_hash,
            "source_archive_file": archive_file,
        }

    except Exception as exc:
        print(f"[ERROR] Failed building {mhtml_path.name}: {exc}")
        traceback.print_exc()
        raise


def write_manifest(
    output_root: Path,
    entries: list[dict[str, object]],
) -> None:
    """Write the staging manifest using the runtime-compatible pages shape."""
    try:
        if not entries:
            raise ValueError("Cannot write an empty staging manifest.")

        manual_toc_url = derive_manual_toc_url(
            str(entries[0]["source_url"])
        )

        manifest = {
            "manual_toc_url": manual_toc_url,
            "source": "manually_archived_mhtml",
            "pages": entries,
        }

        manifest_path = output_root / "manifest.json"

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        print(f"[OK] Staging manifest written: {manifest_path}")

    except Exception as exc:
        print(f"[ERROR] Failed writing staging manifest: {exc}")
        traceback.print_exc()
        raise


def main() -> int:
    """Build an isolated staging corpus without touching active Waypoint data."""
    temporary_dir: Path | None = None

    try:
        print("[START] Building Waypoint staging corpus")
        print("[INFO] NETWORK FREE")
        print(f"[INFO] Source archive: {ARCHIVE_DIR}")
        print(f"[INFO] Final staging directory: {STAGING_DIR}")

        if not ARCHIVE_DIR.exists():
            print(
                f"[ERROR] Source archive does not exist: "
                f"{ARCHIVE_DIR}"
            )
            return 1

        files = sorted(
            ARCHIVE_DIR.glob("*.mhtml"),
            key=lambda path: path.name.lower(),
        )

        if not files:
            print("[ERROR] No MHTML source files found.")
            return 1

        if STAGING_DIR.exists():
            print(
                f"[ERROR] Staging directory already exists: "
                f"{STAGING_DIR}"
            )
            print(
                "[INFO] Refusing to overwrite existing staging data. "
                "Review or remove it explicitly before rebuilding."
            )
            return 1

        print(f"[INFO] MHTML files discovered: {len(files)}")

        temporary_dir = Path(
            tempfile.mkdtemp(
                prefix=".waypoint-staging-",
                dir=DATA_DIR,
            )
        )

        print(
            f"[INFO] Temporary build directory: "
            f"{temporary_dir}"
        )

        entries: list[dict[str, object]] = []

        for index, mhtml_path in enumerate(files, start=1):
            print()
            print(
                f"[{index:03}/{len(files):03}] "
                f"{mhtml_path.name}"
            )

            entry = build_section(
                mhtml_path=mhtml_path,
                output_root=temporary_dir,
            )

            entries.append(entry)

        # Ensure one manifest entry exists for every discovered source file.
        if len(entries) != len(files):
            raise RuntimeError(
                "Staging entry count does not match source archive count."
            )

        section_codes = [
            str(entry["section_code"])
            for entry in entries
        ]

        if len(section_codes) != len(set(section_codes)):
            raise RuntimeError(
                "Duplicate section codes detected in staging corpus."
            )

        write_manifest(
            output_root=temporary_dir,
            entries=entries,
        )

        # Publish staging atomically only after every source has succeeded.
        temporary_dir.replace(STAGING_DIR)
        temporary_dir = None

        missing_dates = [
            entry["section_code"]
            for entry in entries
            if not entry["effective_date"]
        ]

        print()
        print("Staging corpus build")
        print("--------------------")
        print(f"Source MHTML files: {len(files)}")
        print(f"Markdown files:     {len(entries)}")
        print(f"Manifest entries:   {len(entries)}")
        print(f"Missing dates:      {len(missing_dates)}")
        print(f"Staging directory:  {STAGING_DIR}")

        if missing_dates:
            print()
            print("[INFO] Sections without an effective date:")
            for section_code in missing_dates:
                print(f"  {section_code}")

        print()
        print(
            "[OK] Staging corpus generated successfully."
        )
        print(
            "[OK] Active data/manifest.json and active corpus "
            "were not modified."
        )

        return 0

    except Exception as exc:
        print(f"[ERROR] Staging corpus build failed: {exc}")
        traceback.print_exc()

        if temporary_dir is not None and temporary_dir.exists():
            try:
                shutil.rmtree(temporary_dir)
                print(
                    f"[INFO] Removed incomplete temporary build: "
                    f"{temporary_dir}"
                )
            except Exception as cleanup_exc:
                print(
                    f"[ERROR] Failed cleaning temporary build: "
                    f"{cleanup_exc}"
                )
                traceback.print_exc()

        return 1


if __name__ == "__main__":
    sys.exit(main())