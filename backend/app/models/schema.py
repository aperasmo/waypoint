"""Database models for the Waypoint corpus.

Two tables: sections carry the per-page metadata from the manifest, chunks
carry the text and its embedding. The split exists because browse and the
update job both work at section level, not chunk level.
"""

from __future__ import annotations

from datetime import date, datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

EMBEDDING_DIM = 1536


class Base(DeclarativeBase):
    pass


class Section(Base):
    """One page of the INZ Operational Manual, as listed in manifest.json."""

    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True)

    # SR3.10, WA2.10, A5.1. Natural key, so ingest can upsert on it.
    section_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)

    title: Mapped[str] = mapped_column(String(512))
    source_url: Mapped[str] = mapped_column(String(512))

    # Nullable: roughly 20 index pages carry no effective date.
    effective_date: Mapped[date | None] = mapped_column(nullable=True)

    # From the manifest. Lets the update job tell a changed page from an
    # unchanged one without re-reading the file.
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Chunk.chunk_index",
    )


class Chunk(Base):
    """One embeddable piece of a section. Most sections produce exactly one."""

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("section_id", "chunk_index", name="uq_chunk_section_index"),
        Index(
            "ix_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    section_id: Mapped[int] = mapped_column(
        ForeignKey("sections.id", ondelete="CASCADE"), index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer)
    chunk_total: Mapped[int] = mapped_column(Integer)

    # Raw policy text as the chunker produced it. The contextual prefix used
    # for embedding is built at embed time and deliberately not stored, so a
    # prefix format change never needs a data migration.
    text: Mapped[str] = mapped_column(Text)
    char_count: Mapped[int] = mapped_column(Integer)

    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM), nullable=True
    )

    # Which model produced the vector above. Without this you cannot tell a
    # stale embedding from a current one after switching providers.
    embedding_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    embedding_dim: Mapped[int | None] = mapped_column(Integer, nullable=True)

    section: Mapped[Section] = relationship(back_populates="chunks")