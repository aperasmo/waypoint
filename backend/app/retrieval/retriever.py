"""Hybrid retrieval over the INZ corpus.

Vector search catches questions phrased in the user's words ("show money"),
full-text catches exact terms the manual uses verbatim (IELTS, ANZSCO,
PSWV). Neither alone is enough, so results from both are merged.

This is the baseline. Query rewriting and reranking come later, and only
once the evaluation set shows they help.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import Float, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ingestion.embedder import EmbeddingProvider
from app.models.schema import Chunk, Section

from app.retrieval.acronyms import expand_acronyms

# Standard RRF constant. Dampens the influence of top ranks so one search
# leg cannot dominate purely by being confident.
RRF_K = 60

CANDIDATES_PER_LEG = 20


@dataclass(frozen=True)
class Result:
    section_code: str
    title: str
    source_url: str
    effective_date: str | None
    chunk_index: int
    chunk_total: int
    text: str

    score: float
    vector_rank: int | None
    text_rank: int | None

    @property
    def matched_both(self) -> bool:
        """Both legs found it. A useful confidence signal for the ask
        endpoint, since agreement between two different methods is stronger
        evidence than a high score from either alone."""
        return self.vector_rank is not None and self.text_rank is not None


async def _vector_candidates(
    session: AsyncSession, query_vector: list[float], limit: int
) -> list[tuple[Chunk, float]]:
    distance = Chunk.embedding.cosine_distance(query_vector).label("distance")
    stmt = (
        select(Chunk, distance)
        .options(selectinload(Chunk.section))
        .where(Chunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [(chunk, dist) for chunk, dist in rows]


async def _text_candidates(
    session: AsyncSession, query: str, limit: int
) -> list[tuple[Chunk, float]]:
    # websearch_to_tsquery handles ordinary typed input without raising on
    # punctuation, which plainto_tsquery and to_tsquery do not.
    tsquery = func.websearch_to_tsquery("english", query)
    rank = func.ts_rank(Chunk.search_vector, tsquery).cast(Float).label("rank")

    stmt = (
        select(Chunk, rank)
        .options(selectinload(Chunk.section))
        .where(Chunk.search_vector.op("@@")(tsquery))
        .order_by(rank.desc())
        .limit(limit)
    )
    rows = await session.execute(stmt)
    return [(chunk, score) for chunk, score in rows]


def _fuse(
    vector_hits: list[tuple[Chunk, float]],
    text_hits: list[tuple[Chunk, float]],
    limit: int,
) -> list[Result]:
    """Reciprocal Rank Fusion.

    Combines by position, not by score. Cosine distance and ts_rank are on
    incomparable scales, so adding or averaging them would be meaningless.
    Rank is the only common currency.
    """
    scores: dict[int, float] = {}
    chunks: dict[int, Chunk] = {}
    vector_ranks: dict[int, int] = {}
    text_ranks: dict[int, int] = {}

    for position, (chunk, _) in enumerate(vector_hits, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (RRF_K + position)
        chunks[chunk.id] = chunk
        vector_ranks[chunk.id] = position

    for position, (chunk, _) in enumerate(text_hits, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (RRF_K + position)
        chunks[chunk.id] = chunk
        text_ranks[chunk.id] = position

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    results: list[Result] = []
    for chunk_id, score in ordered[:limit]:
        chunk = chunks[chunk_id]
        section: Section = chunk.section
        results.append(
            Result(
                section_code=section.section_code,
                title=section.title,
                source_url=section.source_url,
                effective_date=(
                    section.effective_date.isoformat() if section.effective_date else None
                ),
                chunk_index=chunk.chunk_index,
                chunk_total=chunk.chunk_total,
                text=chunk.text,
                score=score,
                vector_rank=vector_ranks.get(chunk_id),
                text_rank=text_ranks.get(chunk_id),
            )
        )
    return results


async def retrieve(
    session: AsyncSession,
    query: str,
    embedder: EmbeddingProvider,
    limit: int = 5,
) -> list[Result]:
    """Retrieve the most relevant chunks for a question.

    Returns an empty list for an empty query. Does not apply a relevance
    threshold: deciding when the best result is still not good enough is
    the ask endpoint's job, because that decision is about what to tell the
    person, not about what the database contains.
    """
    query = query.strip()
    if not query:
        return []

    expansion = expand_acronyms(query)
    query = expansion.expanded

    query_vector = await embedder.embed_query(query)

    vector_hits = await _vector_candidates(session, query_vector, CANDIDATES_PER_LEG)
    text_hits = await _text_candidates(session, query, CANDIDATES_PER_LEG)

    return _fuse(vector_hits, text_hits, limit)