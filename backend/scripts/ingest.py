"""Load the corpus into Postgres, embedding only what actually changed.

Cost tracks changes, not corpus size. A daily run with no INZ updates makes
zero API calls.
"""

from __future__ import annotations

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


async def load_existing(session: AsyncSession) -> dict[str, Section]:
    result = await session.execute(select(Section))
    return {s.section_code: s for s in result.scalars()}


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
    if any(c.embedding_model != model_name for c in existing.chunks):
        return True, "embedding model changed"
    if any(c.embedding is None for c in existing.chunks):
        return True, "missing embedding"
    return False, "unchanged"

def metadata_changed(
    existing: Section,
    incoming: SourceChunk,
) -> bool:
    """Return True when section metadata changed without requiring re-embedding."""
    return (
        existing.title != incoming.title
        or existing.source_url != incoming.source_url
        or existing.effective_date != incoming.effective_date
    )

async def ingest(force: bool = False, dry_run: bool = False) -> None:
    settings = get_settings()
    embedder = OpenAIEmbedder()

    source_chunks, report = chunk_corpus(settings.manifest_path)

    grouped: dict[str, list[SourceChunk]] = defaultdict(list)
    for chunk in source_chunks:
        grouped[chunk.section_code].append(chunk)

    factory = get_session_factory()
    async with factory() as session:
        existing = await load_existing(session)

        # Load chunks eagerly so needs_work can inspect them without a lazy
        # load, which would fail in async context.
        for section in existing.values():
            await session.refresh(section, ["chunks"])

        pending: dict[str, list[SourceChunk]] = {}
        metadata_updates: dict[str, SourceChunk] = {}
        reasons: dict[str, str] = {}

        for code, chunks in grouped.items():
            section = existing.get(code)

            work, reason = needs_work(
                section,
                chunks,
                embedder.model_name,
                force,
            )

            if work:
                pending[code] = chunks
                reasons[code] = reason
            elif section is not None and metadata_changed(section, chunks[0]):
                metadata_updates[code] = chunks[0]
                reasons[code] = "metadata changed"
            else:
                reasons[code] = reason

        print(f"Sections in corpus:  {len(grouped)}")
        print(f"Chunks in corpus:    {len(source_chunks)}")
        print(f"Sections to embed:   {len(pending)}")
        print(f"Chunks to embed:     {sum(len(v) for v in pending.values())}")
        print(f"Metadata updates:    {len(metadata_updates)}")
        if pending:
            print("\nSections requiring embedding:")
            for code in pending:
                print(f"  {code}: {reasons[code]}")

        if metadata_updates:
            print("\nMetadata-only updates:")
            for code in metadata_updates:
                print(f"  {code}")        
        if report.files_missing:
            print(f"Missing files:       {report.files_missing}")
        if report.files_skipped_empty:
            print(f"Empty sections:      {len(report.files_skipped_empty)} skipped")

        if dry_run:
            print("\nDry run, nothing written.")
            return

        if not pending and not metadata_updates:
            print("\nNothing to do.")
            return

        # Only call the embedding API when section content actually changed.
        # Metadata-only updates should not incur embedding cost.
        flat: list[SourceChunk] = []
        by_code: dict[str, list[list[float]]] = defaultdict(list)

        if pending:
            flat = [c for chunks in pending.values() for c in chunks]
            vectors = await embedder.embed_chunks(flat)

            for chunk, vector in zip(flat, vectors, strict=True):
                by_code[chunk.section_code].append(vector)

        # Metadata changes such as an effective date, title, or source URL do not
        # require replacing chunks or generating new embeddings.
        for code, head in metadata_updates.items():
            section = existing[code]
            section.title = head.title
            section.source_url = head.source_url
            section.effective_date = head.effective_date
            section.content_hash = head.content_hash

        for code, chunks in pending.items():
            head = chunks[0]
            section = existing.get(code)

            is_new = section is None
            if section is None:
                section = Section(section_code=code)
                # chunks is empty by definition on a new row. Setting it
                # explicitly stops SQLAlchemy lazy-loading it later, which
                # is synchronous IO and fails in async context.
                section.chunks = []
                session.add(section)

            section.title = head.title
            section.source_url = head.source_url
            section.effective_date = head.effective_date
            section.content_hash = head.content_hash

            # Replace rather than update. Chunk boundaries move when content
            # changes, so chunk 2 of the old version and chunk 2 of the new
            # one are not the same thing.
            if not is_new:
                section.chunks.clear()
            await session.flush()

            for chunk, vector in zip(chunks, by_code[code], strict=True):
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

        await session.commit()

        print(
            f"\nCommitted {len(pending)} embedded sections, "
            f"{len(flat)} chunks; "
            f"updated metadata for {len(metadata_updates)} sections."
        )       


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest the INZ corpus.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-embed everything. Use after changing chunking rules or the prefix format.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would happen without calling the API or writing.",
    )
    args = parser.parse_args()

    async def run() -> None:
        await ingest(force=args.force, dry_run=args.dry_run)
        await dispose_engine()

    asyncio.run(run())


if __name__ == "__main__":
    main()