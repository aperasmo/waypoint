"""Turn chunk text into vectors.

The provider sits behind a small protocol so swapping it later costs one
re-ingest, not a rewrite. Every chunk row records which model produced its
vector, so stale rows are identifiable after a switch.
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from openai import AsyncOpenAI

from app.config import get_settings
from app.ingestion.chunker import Chunk


class EmbeddingProvider(Protocol):
    """What retrieval and ingestion depend on. Nothing here is OpenAI-specific."""

    @property
    def model_name(self) -> str: ...

    @property
    def dimensions(self) -> int: ...

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...


def build_embedding_input(chunk: Chunk) -> str:
    """Prepend a short anchor so no chunk is ever context-free.

    Forty sections split into multiple pieces, and a middle piece can start
    mid-list with nothing saying what it belongs to. The anchor is added at
    embed time and deliberately not stored, so changing this format only
    needs a re-embed, never a data migration.
    """
    # The manifest title already begins with the section code in most cases.
    title = chunk.title.strip()
    header = title if title.startswith(chunk.section_code) else f"{chunk.section_code}: {title}"
    if chunk.chunk_total > 1:
        header += f" (part {chunk.chunk_index + 1} of {chunk.chunk_total})"
    return f"{header}\n\n{chunk.text}"


class OpenAIEmbedder:
    """OpenAI implementation of EmbeddingProvider."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        dimensions: int | None = None,
        batch_size: int | None = None,
    ) -> None:
        settings = get_settings()
        self._model = model or settings.embedding_model
        self._dimensions = dimensions or settings.embedding_dim
        self._batch_size = batch_size or settings.embedding_batch_size
        self._client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

        # The schema hardcodes the vector width. A mismatch here surfaces as
        # an opaque Postgres error at insert time, so fail early instead.
        from app.models.schema import EMBEDDING_DIM

        if self._dimensions != EMBEDDING_DIM:
            raise ValueError(
                f"Configured embedding_dim ({self._dimensions}) does not match "
                f"the schema's EMBEDDING_DIM ({EMBEDDING_DIM}). Changing this "
                f"requires a schema change and a full re-embed."
            )

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self._dimensions

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        response = await self._client.embeddings.create(input=texts, model=self._model)
        # The API documents order preservation, but sorting by index is cheap
        # insurance against silently misaligned vectors, which would be very
        # hard to notice and very wrong.
        ordered = sorted(response.data, key=lambda item: item.index)
        return [item.embedding for item in ordered]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        results: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            results.extend(await self._embed_batch(batch))
            # Sequential, not concurrent. 194 chunks is two batches, so there
            # is nothing to gain from parallelism and a rate limit to avoid.
            await asyncio.sleep(0)

        if len(results) != len(texts):
            raise RuntimeError(
                f"Embedding count mismatch: sent {len(texts)}, got {len(results)}"
            )
        return results

    async def embed_query(self, text: str) -> list[float]:
        vectors = await self._embed_batch([text])
        return vectors[0]

    async def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Convenience wrapper that applies the contextual anchor."""
        return await self.embed_documents([build_embedding_input(c) for c in chunks])


def get_embedder() -> EmbeddingProvider:
    return OpenAIEmbedder()