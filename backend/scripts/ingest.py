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
        reasons: dict[str, str] = {}

        for code, chunks in grouped.items():
            work, reason = needs_work(existing.get(code), chunks, embedder.model_name, force)
            reasons[code] = reason
            if work:
                pending[code] = chunks

        print(f"Sections in corpus:  {len(grouped)}")
        print(f"Chunks in corpus:    {len(source_chunks)}")
        print(f"Sections to embed:   {len(pending)}")
        print(f"Chunks to embed:     {sum(len(v) for v in pending.values())}")
        if report.files_missing:
            print(f"Missing files:       {report.files_missing}")
        if report.files_skipped_empty:
            print(f"Empty sections:      {len(report.files_skipped_empty)} skipped")

        if dry_run:
            print("\nDry run, nothing written.")
            return

        if not pending:
            print("\nNothing to do.")
            return

        flat = [c for chunks in pending.values() for c in chunks]
        vectors = await embedder.embed_chunks(flat)

        by_code: dict[str, list[list[float]]] = defaultdict(list)
        for chunk, vector in zip(flat, vectors, strict=True):
            by_code[chunk.section_code].append(vector)

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
        print(f"\nCommitted {len(pending)} sections, {len(flat)} chunks.")


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