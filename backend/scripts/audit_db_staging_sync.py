"""
Compare the current Waypoint database section set with the rebuilt staging
corpus.

READ ONLY.

No database rows, embeddings, corpus files, manifests, or frontend files are
modified.
"""

from __future__ import annotations

import asyncio
import sys
import traceback
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from app.db.session import dispose_engine, get_session_factory
from app.ingestion.chunker import chunk_corpus
from app.models.schema import Section


PROJECT_ROOT = Path(__file__).resolve().parents[2]

STAGING_MANIFEST = (
    PROJECT_ROOT
    / "data"
    / "staging"
    / "manifest.json"
)


async def audit() -> int:
    """Compare database section codes with the staging corpus."""
    try:
        print("[START] Auditing database against staging corpus")
        print("[INFO] READ ONLY")
        print(f"[INFO] Staging manifest: {STAGING_MANIFEST}")

        source_chunks, report = chunk_corpus(
            STAGING_MANIFEST
        )

        grouped = defaultdict(list)

        for chunk in source_chunks:
            grouped[chunk.section_code].append(
                chunk
            )

        staging_codes = set(
            grouped.keys()
        )

        factory = get_session_factory()

        async with factory() as session:
            result = await session.execute(
                select(Section)
            )

            sections = list(
                result.scalars()
            )

        database_by_code = {
            section.section_code: section
            for section in sections
        }

        database_codes = set(
            database_by_code.keys()
        )

        stale_database = sorted(
            database_codes - staging_codes
        )

        missing_database = sorted(
            staging_codes - database_codes
        )

        shared = sorted(
            database_codes & staging_codes
        )

        print()
        print("Database / staging sync audit")
        print("-----------------------------")
        print(
            f"Database sections:     {len(database_codes)}"
        )
        print(
            f"Staging sections:      {len(staging_codes)}"
        )
        print(
            f"Shared sections:       {len(shared)}"
        )
        print(
            f"Stale database rows:   {len(stale_database)}"
        )
        print(
            f"Missing database rows: {len(missing_database)}"
        )

        if stale_database:
            print()
            print("[STALE DATABASE SECTIONS]")

            for code in stale_database:
                section = database_by_code[
                    code
                ]

                print(
                    f"  {code}: {section.title}"
                )

        if missing_database:
            print()
            print("[NEW STAGING SECTIONS]")

            for code in missing_database:
                print(
                    f"  {code}"
                )

        if report.files_missing:
            print()
            print(
                "[WARNING] Staging files missing:"
            )

            for path in report.files_missing:
                print(
                    f"  {path}"
                )

        if report.files_skipped_empty:
            print()
            print(
                "[WARNING] Empty staging sections:"
            )

            for path in report.files_skipped_empty:
                print(
                    f"  {path}"
                )

        print()
        print(
            "[OK] Database comparison complete."
        )
        print(
            "[OK] No database rows were modified."
        )

        return 0

    except Exception as exc:
        print(
            f"[ERROR] Database sync audit failed: {exc}"
        )
        traceback.print_exc()
        return 1

    finally:
        await dispose_engine()


def main() -> None:
    """Run the asynchronous database audit."""
    exit_code = asyncio.run(
        audit()
    )

    sys.exit(
        exit_code
    )


if __name__ == "__main__":
    main()