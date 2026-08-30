"""Load the corpus into Postgres, embedding only what actually changed.

Cost tracks changes, not corpus size. A daily run with no INZ updates makes
zero API calls.

Stale database sections are never deleted unless --prune is explicitly used.
"""

from __future__ import annotations
import json
import argparse
import asyncio
from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import dispose_engine, get_session_factory
from app.ingestion.chunker import Chunk as SourceChunk
from app.ingestion.chunker import chunk_corpus
from app.ingestion.embedder import OpenAIEmbedder
from app.models.schema import Chunk, Section


async def load_existing(
    session: AsyncSession,
) -> dict[str, Section]:
    """Load all currently stored sections keyed by section code."""
    result = await session.execute(
        select(Section)
    )

    return {
        section.section_code: section
        for section in result.scalars()
    }

def load_manifest_codes(manifest_path) -> set[str]:
    """Load every declared section code from the current manifest."""
    data = json.loads(
        manifest_path.read_text(
            encoding="utf-8"
        )
    )

    pages = data.get("pages")

    if not isinstance(pages, list):
        raise ValueError(
            "Manifest does not contain a valid pages list."
        )

    codes = {
        str(page.get("section_code", "")).strip()
        for page in pages
        if str(page.get("section_code", "")).strip()
    }

    if not codes:
        raise ValueError(
            "Manifest contains no section codes."
        )

    return codes

def needs_work(
    existing: Section | None,
    incoming: list[SourceChunk],
    model_name: str,
    force: bool,
) -> tuple[bool, str]:
    """Decide whether a section needs re-embedding, and say why.

    The hash catches INZ content changes. It does not catch our own chunking
    or prefix changes, which is what force is for, nor a provider switch,
    which the model-name check handles.
    """
    if existing is None:
        return True, "new"

    if force:
        return True, "forced"

    if existing.content_hash != incoming[0].content_hash:
        return True, "content changed"

    if any(
        chunk.embedding_model != model_name
        for chunk in existing.chunks
    ):
        return True, "embedding model changed"

    if any(
        chunk.embedding is None
        for chunk in existing.chunks
    ):
        return True, "missing embedding"

    return False, "unchanged"


def metadata_changed(
    existing: Section,
    incoming: SourceChunk,
) -> bool:
    """Return True when metadata changed without requiring re-embedding."""
    return (
        existing.title != incoming.title
        or existing.source_url != incoming.source_url
        or existing.effective_date != incoming.effective_date
    )


async def ingest(
    force: bool = False,
    dry_run: bool = False,
    prune: bool = False,
) -> None:
    """Synchronise the configured corpus with the database."""
    settings = get_settings()
    embedder = OpenAIEmbedder()

    source_chunks, report = chunk_corpus(
        settings.manifest_path
    )

    manifest_codes = load_manifest_codes(
        settings.manifest_path
    )

    grouped: dict[str, list[SourceChunk]] = defaultdict(list)

    for chunk in source_chunks:
        grouped[chunk.section_code].append(
            chunk
        )

    # Pruning should never run against a visibly incomplete corpus.
    if prune:
        if not manifest_codes:
            raise RuntimeError(
                "Refusing to prune because the manifest contains no sections."
            )

        if report.files_missing:
            raise RuntimeError(
                "Refusing to prune because corpus files are missing: "
                f"{report.files_missing}"
            )

    factory = get_session_factory()

    async with factory() as session:
        existing = await load_existing(
            session
        )

        # Load chunks eagerly so needs_work can inspect them without a lazy
        # load, which would fail in async context.
        for section in existing.values():
            await session.refresh(
                section,
                ["chunks"],
            )

        pending: dict[str, list[SourceChunk]] = {}
        metadata_updates: dict[str, SourceChunk] = {}
        reasons: dict[str, str] = {}

        existing_codes = set(
            existing.keys()
        )

        # Pruning follows the manifest, not only sections that produced chunks.
        # Navigation/index entries may legitimately exist in the manifest while
        # producing no searchable chunks.
        stale_codes = sorted(
            existing_codes - manifest_codes
        )

        for code, chunks in grouped.items():
            section = existing.get(
                code
            )

            work, reason = needs_work(
                section,
                chunks,
                embedder.model_name,
                force,
            )

            if work:
                pending[code] = chunks
                reasons[code] = reason

            elif (
                section is not None
                and metadata_changed(
                    section,
                    chunks[0],
                )
            ):
                metadata_updates[code] = chunks[0]
                reasons[code] = "metadata changed"

            else:
                reasons[code] = reason

        print(
            f"Sections in corpus:  {len(grouped)}"
        )
        print(
            f"Chunks in corpus:    {len(source_chunks)}"
        )
        print(
            f"Sections to embed:   {len(pending)}"
        )
        print(
            "Chunks to embed:     "
            f"{sum(len(value) for value in pending.values())}"
        )
        print(
            f"Metadata updates:    {len(metadata_updates)}"
        )
        print(
            f"Stale DB sections:   {len(stale_codes)}"
        )

        if pending:
            print()
            print(
                "Sections requiring embedding:"
            )

            for code in pending:
                print(
                    f"  {code}: {reasons[code]}"
                )

        if metadata_updates:
            print()
            print(
                "Metadata-only updates:"
            )

            for code in metadata_updates:
                print(
                    f"  {code}"
                )

        if stale_codes:
            print()
            print(
                "Stale database sections:"
            )

            for code in stale_codes:
                section = existing[
                    code
                ]

                print(
                    f"  {code}: {section.title}"
                )

            if prune:
                print(
                    "\nPrune enabled: stale sections "
                    "will be deleted."
                )
            else:
                print(
                    "\nPrune disabled: stale sections "
                    "will be retained."
                )

        if report.files_missing:
            print(
                f"Missing files:       {report.files_missing}"
            )

        if report.files_skipped_empty:
            print(
                "Empty sections:      "
                f"{len(report.files_skipped_empty)} skipped"
            )

        if dry_run:
            print(
                "\nDry run, nothing written."
            )
            return

        has_prune_work = (
            prune
            and bool(stale_codes)
        )

        if (
            not pending
            and not metadata_updates
            and not has_prune_work
        ):
            print(
                "\nNothing to do."
            )
            return

        # Generate embeddings before modifying database state. If the API call
        # fails, no section deletion or metadata update has occurred.
        flat: list[SourceChunk] = []
        by_code: dict[str, list[list[float]]] = defaultdict(list)

        if pending:
            flat = [
                chunk
                for chunks in pending.values()
                for chunk in chunks
            ]

            vectors = await embedder.embed_chunks(
                flat
            )

            for chunk, vector in zip(
                flat,
                vectors,
                strict=True,
            ):
                by_code[
                    chunk.section_code
                ].append(
                    vector
                )

        # Metadata-only changes do not require new embeddings.
        for code, head in metadata_updates.items():
            section = existing[
                code
            ]

            section.title = head.title
            section.source_url = head.source_url
            section.effective_date = head.effective_date
            section.content_hash = head.content_hash

        for code, chunks in pending.items():
            head = chunks[0]
            section = existing.get(
                code
            )

            is_new = section is None

            if section is None:
                section = Section(
                    section_code=code
                )

                # New sections have no chunks. Assigning the empty collection
                # avoids an async lazy-load when chunks are appended below.
                section.chunks = []

                session.add(
                    section
                )

            section.title = head.title
            section.source_url = head.source_url
            section.effective_date = head.effective_date
            section.content_hash = head.content_hash

            # Replace rather than update. Chunk boundaries move when content
            # changes, so old and new chunk indexes are not interchangeable.
            if not is_new:
                section.chunks.clear()

            await session.flush()

            for chunk, vector in zip(
                chunks,
                by_code[code],
                strict=True,
            ):
                section.chunks.append(
                    Chunk(
                        chunk_index=chunk.chunk_index,
                        chunk_total=chunk.chunk_total,
                        text=chunk.text,
                        char_count=chunk.char_count,
                        embedding=vector,
                        embedding_model=embedder.model_name,
                        embedding_dim=embedder.dimensions,
                    )
                )

        deleted_count = 0

        if prune:
            for code in stale_codes:
                await session.delete(
                    existing[code]
                )

                deleted_count += 1

        await session.commit()

        print(
            f"\nCommitted {len(pending)} embedded sections, "
            f"{len(flat)} chunks; "
            f"updated metadata for {len(metadata_updates)} sections; "
            f"pruned {deleted_count} stale sections."
        )


def main() -> None:
    """Parse CLI options and run ingestion."""
    parser = argparse.ArgumentParser(
        description="Ingest the INZ corpus."
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Re-embed everything. Use after changing chunking "
            "rules or the prefix format."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Report what would happen without calling the API "
            "or writing."
        ),
    )

    parser.add_argument(
        "--prune",
        action="store_true",
        help=(
            "Delete database sections that are no longer present "
            "in the current manifest."
        ),
    )

    args = parser.parse_args()

    async def run() -> None:
        await ingest(
            force=args.force,
            dry_run=args.dry_run,
            prune=args.prune,
        )

        await dispose_engine()

    asyncio.run(
        run()
    )


if __name__ == "__main__":
    main()