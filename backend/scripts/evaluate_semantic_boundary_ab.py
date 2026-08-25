"""A/B retrieval evaluation for Waypoint semantic boundary shifts.

This experiment compares the live production retriever with the constrained
semantic-boundary candidate using the same frozen retrieval questions.

Controls:
- same eval_questions.json
- same acronym expansion
- same query embedding vector for production and candidate
- same text-embedding model
- unchanged candidate chunks reuse their stored production embeddings exactly
- changed chunks alone are re-embedded
- same PostgreSQL websearch_to_tsquery('english', ...)
- same ts_rank
- same vector cosine operator
- same HNSW index parameters
- same GIN FTS index
- same 20 candidates per leg
- same RRF K=60
- same top-5 scoring
- exactly the same total number of chunks

The candidate exists only in a PostgreSQL TEMP table inside an uncommitted
transaction. No production rows, corpus files, manifest entries, stored
embeddings, retriever code, or evaluation questions are modified.

Prerequisite:
    scripts/compare_boundary_shifts_constrained.py

Run from backend/:
    uv run python -m scripts.evaluate_semantic_boundary_ab
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder, build_embedding_input
from app.models.schema import Chunk as DbChunk, EMBEDDING_DIM
from app.retrieval.acronyms import expand_acronyms
from app.retrieval.retriever import CANDIDATES_PER_LEG, RRF_K, retrieve

from scripts.compare_boundary_shifts_constrained import (
    MAX_CHARS,
    OVERLAP_CHARS,
    SHIFT_WINDOW_CHARS,
    all_accepted_balances_safe,
    boundary_offsets,
    cosine_distance,
    imbalance,
    legal_units,
    load_sections,
    production_boundary_lines,
    rebuild_chunks,
    source_lines,
)


QUESTIONS_PATH = Path(__file__).parent.parent / "tests" / "eval_questions.json"
MANIFEST_PATH = Path(__file__).parent.parent.parent / "data" / "manifest.json"


@dataclass(frozen=True)
class EmbeddingChunk:
    section_code: str
    title: str
    chunk_index: int
    chunk_total: int
    text: str


@dataclass(frozen=True)
class CandidateHit:
    id: int
    section_code: str
    chunk_index: int
    chunk_total: int
    text: str
    score: float
    vector_rank: int | None
    text_rank: int | None


class QueryCachingEmbedder:
    def __init__(self, delegate: OpenAIEmbedder) -> None:
        self.delegate = delegate
        self.model_name = delegate.model_name
        self._query_cache: dict[str, list[float]] = {}

    async def embed_query(self, value: str) -> list[float]:
        if value not in self._query_cache:
            self._query_cache[value] = await self.delegate.embed_query(value)
        return self._query_cache[value]

    async def embed_documents(self, values: list[str]) -> list[list[float]]:
        return await self.delegate.embed_documents(values)


def vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(str(float(value)) for value in vector) + "]"


async def build_candidate_sections(
    embedder: OpenAIEmbedder,
) -> tuple[dict[str, list[str]], int]:
    sections, production_total = load_sections(MANIFEST_PATH)
    split_sections = [s for s in sections if len(s.baseline_chunks) > 1]

    units_by_code = {}
    inputs: list[str] = []
    locations: list[tuple[str, int]] = []

    for section in split_sections:
        units = legal_units(section.body)
        units_by_code[section.section_code] = units

        for index, unit in enumerate(units):
            inputs.append(
                f"{section.section_code}: {section.title}\n\n{unit.text}"
            )
            locations.append((section.section_code, index))

    print(f"Embedding {len(inputs)} legal units for boundary selection...")
    vectors = await embedder.embed_documents(inputs)

    if len(vectors) != len(inputs):
        raise RuntimeError(
            f"Expected {len(inputs)} legal-unit embeddings, got {len(vectors)}"
        )

    vectors_by_location = dict(zip(locations, vectors, strict=True))

    candidate_by_code: dict[str, list[str]] = {}
    accepted_shift_count = 0

    for section in sections:
        baseline_count = len(section.baseline_chunks)

        if baseline_count == 1:
            candidate_by_code[section.section_code] = [section.body]
            continue

        lines = source_lines(section.body)
        offsets = boundary_offsets(lines)
        production_boundaries = production_boundary_lines(section.body)

        if len(production_boundaries) != baseline_count - 1:
            raise RuntimeError(
                f"{section.section_code}: production boundary count "
                f"{len(production_boundaries)} != expected {baseline_count - 1}"
            )

        reconstructed = rebuild_chunks(
            lines,
            production_boundaries,
            OVERLAP_CHARS,
        )
        if reconstructed != section.baseline_chunks:
            raise RuntimeError(
                f"{section.section_code}: production reconstruction mismatch. "
                "A/B comparison aborted."
            )

        units = units_by_code[section.section_code]
        safe_scores: dict[int, float] = {}

        for index in range(1, len(units)):
            line_index = units[index].start_line
            safe_scores[line_index] = cosine_distance(
                vectors_by_location[(section.section_code, index - 1)],
                vectors_by_location[(section.section_code, index)],
            )

        chosen_boundaries = list(production_boundaries)
        accepted_numbers: set[int] = set()

        for boundary_number, production_line in enumerate(
            production_boundaries,
            start=1,
        ):
            production_offset = offsets[production_line]

            previous_offset = (
                offsets[production_boundaries[boundary_number - 2]]
                if boundary_number > 1
                else 0
            )
            next_offset = (
                offsets[production_boundaries[boundary_number]]
                if boundary_number < len(production_boundaries)
                else len(section.body)
            )

            lower_guard = (previous_offset + production_offset) // 2
            upper_guard = (production_offset + next_offset) // 2

            nearby: list[tuple[float, int, int]] = []

            for safe_line, distance in safe_scores.items():
                safe_offset = offsets[safe_line]
                delta = safe_offset - production_offset

                if safe_line == production_line:
                    continue
                if abs(delta) > SHIFT_WINDOW_CHARS:
                    continue
                if not lower_guard < safe_offset < upper_guard:
                    continue

                nearby.append((distance, -abs(delta), safe_line))

            for _, _, safe_line in sorted(
                nearby,
                key=lambda item: (item[0], item[1]),
                reverse=True,
            ):
                trial_boundaries = list(chosen_boundaries)
                trial_boundaries[boundary_number - 1] = safe_line

                if trial_boundaries != sorted(trial_boundaries):
                    continue
                if len(set(trial_boundaries)) != len(trial_boundaries):
                    continue

                trial_chunks = rebuild_chunks(
                    lines,
                    trial_boundaries,
                    OVERLAP_CHARS,
                )

                if len(trial_chunks) != baseline_count:
                    continue
                if any(len(chunk) > MAX_CHARS for chunk in trial_chunks):
                    continue

                left = boundary_number - 1
                right = boundary_number

                production_balance = imbalance(
                    len(section.baseline_chunks[left]),
                    len(section.baseline_chunks[right]),
                )
                trial_balance = imbalance(
                    len(trial_chunks[left]),
                    len(trial_chunks[right]),
                )

                if trial_balance > production_balance:
                    continue

                trial_accepted = set(accepted_numbers)
                trial_accepted.add(boundary_number)

                if not all_accepted_balances_safe(
                    trial_chunks,
                    section.baseline_chunks,
                    trial_accepted,
                ):
                    continue

                chosen_boundaries = trial_boundaries
                accepted_numbers = trial_accepted
                accepted_shift_count += 1
                break

        final_chunks = rebuild_chunks(
            lines,
            chosen_boundaries,
            OVERLAP_CHARS,
        )

        if len(final_chunks) != baseline_count:
            raise RuntimeError(
                f"{section.section_code}: candidate chunk count changed"
            )
        if any(len(chunk) > MAX_CHARS for chunk in final_chunks):
            raise RuntimeError(
                f"{section.section_code}: candidate exceeds MAX_CHARS"
            )
        if not all_accepted_balances_safe(
            final_chunks,
            section.baseline_chunks,
            accepted_numbers,
        ):
            raise RuntimeError(
                f"{section.section_code}: final balance guard failed"
            )

        candidate_by_code[section.section_code] = final_chunks

    candidate_total = sum(len(chunks) for chunks in candidate_by_code.values())

    if candidate_total != production_total:
        raise RuntimeError(
            f"Candidate has {candidate_total} chunks; "
            f"production has {production_total}"
        )

    return candidate_by_code, accepted_shift_count


async def load_production_chunks(session) -> dict[tuple[str, int], DbChunk]:
    stmt = (
        select(DbChunk)
        .options(selectinload(DbChunk.section))
        .order_by(DbChunk.section_id, DbChunk.chunk_index)
    )
    rows = await session.execute(stmt)
    chunks = list(rows.scalars())

    result: dict[tuple[str, int], DbChunk] = {}
    for chunk in chunks:
        result[(chunk.section.section_code, chunk.chunk_index)] = chunk
    return result


async def prepare_candidate_rows(
    session,
    candidate_by_code: dict[str, list[str]],
    embedder: OpenAIEmbedder,
) -> tuple[list[dict], int, int]:
    production = await load_production_chunks(session)

    expected_count = sum(len(chunks) for chunks in candidate_by_code.values())
    if len(production) != expected_count:
        raise RuntimeError(
            f"Database has {len(production)} chunks; "
            f"candidate expects {expected_count}"
        )

    rows: list[dict] = []
    changed_inputs: list[str] = []
    changed_row_positions: list[int] = []
    reused = 0
    next_id = 1

    for section_code, texts in candidate_by_code.items():
        chunk_total = len(texts)

        for chunk_index, chunk_text in enumerate(texts):
            key = (section_code, chunk_index)
            production_chunk = production.get(key)

            if production_chunk is None:
                raise RuntimeError(f"Missing production chunk {key}")
            if production_chunk.embedding is None:
                raise RuntimeError(
                    f"Production embedding is null for {section_code} "
                    f"chunk {chunk_index}"
                )
            if production_chunk.embedding_dim != EMBEDDING_DIM:
                raise RuntimeError(
                    f"Unexpected production embedding dimension for "
                    f"{section_code} chunk {chunk_index}: "
                    f"{production_chunk.embedding_dim}"
                )

            title = production_chunk.section.title

            row = {
                "id": next_id,
                "section_code": section_code,
                "title": title,
                "chunk_index": chunk_index,
                "chunk_total": chunk_total,
                "text": chunk_text,
                "embedding": None,
            }

            if chunk_text == production_chunk.text:
                row["embedding"] = vector_literal(
                    [float(v) for v in production_chunk.embedding]
                )
                reused += 1
            else:
                embedding_chunk = EmbeddingChunk(
                    section_code=section_code,
                    title=title,
                    chunk_index=chunk_index,
                    chunk_total=chunk_total,
                    text=chunk_text,
                )
                changed_inputs.append(build_embedding_input(embedding_chunk))
                changed_row_positions.append(len(rows))

            rows.append(row)
            next_id += 1

    if changed_inputs:
        print(
            f"Embedding {len(changed_inputs)} changed candidate chunks; "
            f"reusing {reused} stored production vectors..."
        )
        changed_vectors = await embedder.embed_documents(changed_inputs)

        if len(changed_vectors) != len(changed_inputs):
            raise RuntimeError(
                f"Expected {len(changed_inputs)} changed embeddings, "
                f"got {len(changed_vectors)}"
            )

        for row_position, vector in zip(
            changed_row_positions,
            changed_vectors,
            strict=True,
        ):
            rows[row_position]["embedding"] = vector_literal(vector)
    else:
        print(
            f"No candidate chunk text changed; reusing all {reused} "
            "stored production vectors."
        )

    if any(row["embedding"] is None for row in rows):
        raise RuntimeError("Candidate embedding preparation incomplete")

    return rows, reused, len(changed_inputs)


async def create_temp_candidate_table(session, rows: list[dict]) -> str:
    suffix = uuid.uuid4().hex[:10]
    table_name = f"tmp_waypoint_semantic_ab_{suffix}"
    vector_index = f"{table_name}_embedding_hnsw"
    fts_index = f"{table_name}_search_vector_gin"

    await session.execute(
        text(
            f"""
            CREATE TEMP TABLE {table_name} (
                id integer PRIMARY KEY,
                section_code varchar(32) NOT NULL,
                title varchar(512) NOT NULL,
                chunk_index integer NOT NULL,
                chunk_total integer NOT NULL,
                text text NOT NULL,
                search_vector tsvector GENERATED ALWAYS AS
                    (to_tsvector('english', text)) STORED,
                embedding vector({EMBEDDING_DIM}) NOT NULL
            ) ON COMMIT DROP
            """
        )
    )

    insert_stmt = text(
        f"""
        INSERT INTO {table_name} (
            id,
            section_code,
            title,
            chunk_index,
            chunk_total,
            text,
            embedding
        )
        VALUES (
            :id,
            :section_code,
            :title,
            :chunk_index,
            :chunk_total,
            :text,
            CAST(:embedding AS vector)
        )
        """
    )
    await session.execute(insert_stmt, rows)

    await session.execute(
        text(
            f"""
            CREATE INDEX {vector_index}
            ON {table_name}
            USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64)
            """
        )
    )
    await session.execute(
        text(
            f"""
            CREATE INDEX {fts_index}
            ON {table_name}
            USING gin (search_vector)
            """
        )
    )
    await session.execute(text(f"ANALYZE {table_name}"))

    return table_name


async def candidate_vector_hits(
    session,
    table_name: str,
    query_vector: list[float],
) -> list[dict]:
    stmt = text(
        f"""
        SELECT
            id,
            section_code,
            title,
            chunk_index,
            chunk_total,
            text,
            embedding <=> CAST(:query_vector AS vector) AS distance
        FROM {table_name}
        WHERE embedding IS NOT NULL
        ORDER BY distance
        LIMIT {CANDIDATES_PER_LEG}
        """
    )

    rows = await session.execute(
        stmt,
        {"query_vector": vector_literal(query_vector)},
    )
    return [dict(row._mapping) for row in rows]


async def candidate_text_hits(
    session,
    table_name: str,
    query: str,
) -> list[dict]:
    stmt = text(
        f"""
        WITH q AS (
            SELECT websearch_to_tsquery('english', :query) AS tsquery
        )
        SELECT
            t.id,
            t.section_code,
            t.title,
            t.chunk_index,
            t.chunk_total,
            t.text,
            CAST(ts_rank(t.search_vector, q.tsquery) AS float) AS rank
        FROM {table_name} AS t
        CROSS JOIN q
        WHERE t.search_vector @@ q.tsquery
        ORDER BY rank DESC
        LIMIT {CANDIDATES_PER_LEG}
        """
    )

    rows = await session.execute(stmt, {"query": query})
    return [dict(row._mapping) for row in rows]


def fuse_candidate(
    vector_hits: list[dict],
    text_hits: list[dict],
    limit: int,
) -> list[CandidateHit]:
    scores: dict[int, float] = {}
    chunks: dict[int, dict] = {}
    vector_ranks: dict[int, int] = {}
    text_ranks: dict[int, int] = {}

    for position, chunk in enumerate(vector_hits, start=1):
        chunk_id = int(chunk["id"])
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (
            RRF_K + position
        )
        chunks[chunk_id] = chunk
        vector_ranks[chunk_id] = position

    for position, chunk in enumerate(text_hits, start=1):
        chunk_id = int(chunk["id"])
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (
            RRF_K + position
        )
        chunks[chunk_id] = chunk
        text_ranks[chunk_id] = position

    ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)

    results: list[CandidateHit] = []
    for chunk_id, score in ordered[:limit]:
        chunk = chunks[chunk_id]
        results.append(
            CandidateHit(
                id=chunk_id,
                section_code=str(chunk["section_code"]),
                chunk_index=int(chunk["chunk_index"]),
                chunk_total=int(chunk["chunk_total"]),
                text=str(chunk["text"]),
                score=score,
                vector_rank=vector_ranks.get(chunk_id),
                text_rank=text_ranks.get(chunk_id),
            )
        )
    return results


async def candidate_retrieve(
    session,
    table_name: str,
    query: str,
    embedder: QueryCachingEmbedder,
    limit: int = 5,
) -> list[CandidateHit]:
    query = query.strip()
    if not query:
        return []

    expansion = expand_acronyms(query)
    expanded_query = expansion.expanded
    query_vector = await embedder.embed_query(expanded_query)

    vector_hits = await candidate_vector_hits(
        session,
        table_name,
        query_vector,
    )
    text_hits = await candidate_text_hits(
        session,
        table_name,
        expanded_query,
    )

    return fuse_candidate(vector_hits, text_hits, limit)


def score(
    cases: list[dict],
    results_by_question: dict[str, list[str]],
) -> tuple[int, int]:
    hits_at_1 = 0
    hits_at_5 = 0

    for case in cases:
        expected = set(case["expected_sections"])
        retrieved = results_by_question[case["question"]]

        if retrieved and retrieved[0] in expected:
            hits_at_1 += 1

        if expected & set(retrieved):
            hits_at_5 += 1

    return hits_at_1, hits_at_5


async def main() -> None:
    payload = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))
    cases = payload["questions"]
    answerable = [case for case in cases if case["expected_sections"]]
    gaps = [case for case in cases if not case["expected_sections"]]

    base_embedder = OpenAIEmbedder()
    query_embedder = QueryCachingEmbedder(base_embedder)

    print("Waypoint semantic-boundary retrieval A/B")
    print("=" * 40)
    print(f"Questions:                 {QUESTIONS_PATH}")
    print(f"Embedding model:           {base_embedder.model_name}")
    print(f"Embedding dimension:       {EMBEDDING_DIM}")
    print(f"Candidates per leg:        {CANDIDATES_PER_LEG}")
    print(f"RRF K:                     {RRF_K}")
    print(f"Boundary shift window:     +/- {SHIFT_WINDOW_CHARS} chars")
    print()

    candidate_by_code, accepted_shifts = await build_candidate_sections(
        base_embedder
    )
    candidate_chunk_total = sum(
        len(chunks) for chunks in candidate_by_code.values()
    )

    print(f"Candidate chunks:          {candidate_chunk_total}")
    print(f"Accepted boundary shifts:  {accepted_shifts}")

    factory = get_session_factory()

    try:
        async with factory() as session:
            print()
            print("Running production retrieval...")

            production_answerable: dict[str, list[str]] = {}
            production_gaps: dict[str, list[str]] = {}

            for case in answerable:
                hits = await retrieve(
                    session,
                    case["question"],
                    query_embedder,
                    limit=5,
                )
                production_answerable[case["question"]] = [
                    hit.section_code for hit in hits
                ]

            for case in gaps:
                hits = await retrieve(
                    session,
                    case["question"],
                    query_embedder,
                    limit=3,
                )
                production_gaps[case["question"]] = [
                    hit.section_code for hit in hits
                ]

            rows, reused, reembedded = await prepare_candidate_rows(
                session,
                candidate_by_code,
                base_embedder,
            )

            print(f"Stored vectors reused:     {reused}")
            print(f"Candidate vectors new:     {reembedded}")
            print()
            print("Creating temporary candidate retrieval table...")

            table_name = await create_temp_candidate_table(session, rows)

            print("Running candidate retrieval...")

            candidate_answerable: dict[str, list[str]] = {}
            candidate_gaps: dict[str, list[str]] = {}

            for case in answerable:
                hits = await candidate_retrieve(
                    session,
                    table_name,
                    case["question"],
                    query_embedder,
                    limit=5,
                )
                candidate_answerable[case["question"]] = [
                    hit.section_code for hit in hits
                ]

            for case in gaps:
                hits = await candidate_retrieve(
                    session,
                    table_name,
                    case["question"],
                    query_embedder,
                    limit=3,
                )
                candidate_gaps[case["question"]] = [
                    hit.section_code for hit in hits
                ]

            prod_r1, prod_r5 = score(answerable, production_answerable)
            cand_r1, cand_r5 = score(answerable, candidate_answerable)
            total = len(answerable)

            print()
            print("Retrieval results")
            print("-" * 76)
            print(f"{'':26} {'Production':>20} {'Candidate':>20}")
            print(
                f"{'Recall@1':26} "
                f"{prod_r1:>2}/{total:<2} ({prod_r1 / total:>5.0%}) "
                f"{cand_r1:>8}/{total:<2} ({cand_r1 / total:>5.0%})"
            )
            print(
                f"{'Recall@5':26} "
                f"{prod_r5:>2}/{total:<2} ({prod_r5 / total:>5.0%}) "
                f"{cand_r5:>8}/{total:<2} ({cand_r5 / total:>5.0%})"
            )
            print(
                f"{'Recall@1 delta':26} {cand_r1 - prod_r1:>22}"
            )
            print(
                f"{'Recall@5 delta':26} {cand_r5 - prod_r5:>22}"
            )

            rank1_gains = []
            rank1_regressions = []
            top5_regressions = []
            changed_misses = []

            for case in answerable:
                question = case["question"]
                expected = set(case["expected_sections"])
                prod = production_answerable[question]
                cand = candidate_answerable[question]

                prod_r1_ok = bool(prod and prod[0] in expected)
                cand_r1_ok = bool(cand and cand[0] in expected)
                prod_r5_ok = bool(expected & set(prod))
                cand_r5_ok = bool(expected & set(cand))

                record = (
                    question,
                    case["expected_sections"],
                    prod,
                    cand,
                )

                if not prod_r1_ok and cand_r1_ok:
                    rank1_gains.append(record)
                elif prod_r1_ok and not cand_r1_ok:
                    rank1_regressions.append(record)
                elif not prod_r1_ok and not cand_r1_ok and prod != cand:
                    changed_misses.append(record)

                if prod_r5_ok and not cand_r5_ok:
                    top5_regressions.append(record)

            def print_records(title: str, records: list) -> None:
                if not records:
                    print()
                    print(f"{title}: none")
                    return

                print()
                print(f"{title} ({len(records)})")
                print("-" * 76)

                for question, expected, prod, cand in records:
                    print(question)
                    print(f"    wanted:     {', '.join(expected)}")
                    print(
                        f"    production: "
                        f"{', '.join(prod[:5]) or '(nothing)'}"
                    )
                    print(
                        f"    candidate : "
                        f"{', '.join(cand[:5]) or '(nothing)'}"
                    )

            print_records("Rank-1 gains", rank1_gains)
            print_records("Rank-1 regressions", rank1_regressions)
            print_records("Top-5 regressions", top5_regressions)
            print_records("Changed rank-1 misses", changed_misses)

            gap_changes = []
            for case in gaps:
                question = case["question"]
                prod = production_gaps[question]
                cand = candidate_gaps[question]
                if prod != cand:
                    gap_changes.append((question, prod, cand))

            if gap_changes:
                print()
                print(f"Known-gap retrieval changes ({len(gap_changes)})")
                print("-" * 76)
                for question, prod, cand in gap_changes:
                    print(question)
                    print(
                        f"    production: "
                        f"{', '.join(prod) or '(nothing)'}"
                    )
                    print(
                        f"    candidate : "
                        f"{', '.join(cand) or '(nothing)'}"
                    )

            print()
            print("Decision")
            print("-" * 76)

            if cand_r5 < prod_r5 or cand_r1 < prod_r1:
                verdict = "REJECT"
                reason = "Candidate regressed a frozen retrieval metric."
            elif cand_r5 == prod_r5 and cand_r1 > prod_r1:
                verdict = "MEASURED GAIN"
                reason = "Recall@5 was preserved and Recall@1 improved."
            elif cand_r5 == prod_r5 and cand_r1 == prod_r1:
                verdict = "NO MEASURED GAIN"
                reason = "Frozen Recall@1 and Recall@5 did not improve."
            else:
                verdict = "REVIEW"
                reason = "Metrics changed in a way requiring manual review."

            print(f"Verdict: {verdict}")
            print(f"Reason:  {reason}")

            await session.rollback()

            print()
            print(
                "Read-only A/B complete. Temporary database objects were "
                "rolled back; production rows were not changed."
            )

    finally:
        await dispose_engine()


if __name__ == "__main__":
    asyncio.run(main())