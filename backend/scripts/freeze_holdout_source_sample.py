"""Freeze a deterministic source sample for a fresh Waypoint holdout.

Purpose
-------
Create a new holdout source pool without hand-picking policy sections.

The script:
- reads the adjudicated development benchmark only to identify section codes
  already used as development gold;
- reads substantive sections/chunks from the current Waypoint database;
- excludes development-gold sections;
- deterministically selects N remaining sections using SHA256 ordering;
- writes their real chunk text to a frozen JSON artifact;
- never calls retrieval, embeddings, the reranker, or the answer model;
- never writes to the database.

The selected section codes become source material for authoring fresh holdout
questions. The holdout questions themselves are created only after this source
sample is frozen.

Run from backend/:
    uv run python -m scripts.freeze_holdout_source_sample

Optional:
    uv run python -m scripts.freeze_holdout_source_sample --count 30
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select

from app.db.session import dispose_engine, get_session_factory
from app.models.schema import Chunk, Section


BACKEND_DIR = Path(__file__).resolve().parent.parent
DEV_GOLD_PATH = BACKEND_DIR / "tests" / "eval_questions_adjudicated_v2.json"
DEFAULT_OUTPUT = BACKEND_DIR / "tests" / "holdout_source_sample_v1.json"
DEFAULT_COUNT = 30
DEFAULT_SEED = "waypoint-holdout-source-v1-2026-08-20"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def selection_key(seed: str, section_code: str) -> str:
    payload = f"{seed}|{section_code}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_development_sections(path: Path) -> set[str]:
    if not path.exists():
        raise SystemExit(f"Development benchmark not found: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    questions = payload.get("questions")

    if not isinstance(questions, list):
        raise RuntimeError(
            "Unexpected development benchmark schema: no questions list."
        )

    section_codes: set[str] = set()

    for index, case in enumerate(questions, start=1):
        if not isinstance(case, dict):
            raise RuntimeError(
                f"Development benchmark question {index} is not an object."
            )

        expected = case.get("expected_sections")
        if not isinstance(expected, list):
            raise RuntimeError(
                f"Development question {index} has invalid expected_sections."
            )

        for code in expected:
            if not isinstance(code, str) or not code.strip():
                raise RuntimeError(
                    f"Development question {index} contains invalid section code."
                )
            section_codes.add(code.strip())

    return section_codes


async def load_substantive_sections() -> dict[str, dict]:
    factory = get_session_factory()

    rows_by_section: dict[str, dict] = {}
    chunks_by_section: dict[str, list[dict]] = defaultdict(list)

    try:
        async with factory() as session:
            stmt = (
                select(
                    Section.section_code,
                    Section.title,
                    Chunk.chunk_index,
                    Chunk.chunk_total,
                    Chunk.text,
                )
                .join(Chunk, Chunk.section_id == Section.id)
                .order_by(Section.section_code, Chunk.chunk_index)
            )

            result = await session.execute(stmt)

            for (
                section_code,
                title,
                chunk_index,
                chunk_total,
                text,
            ) in result.all():
                if not isinstance(section_code, str) or not section_code.strip():
                    raise RuntimeError("Database returned invalid section_code.")
                if not isinstance(title, str):
                    raise RuntimeError(
                        f"{section_code}: database returned invalid title."
                    )
                if not isinstance(text, str) or not text.strip():
                    raise RuntimeError(
                        f"{section_code}: database returned empty chunk text."
                    )

                code = section_code.strip()

                existing = rows_by_section.get(code)
                metadata = {
                    "section_code": code,
                    "title": title.strip(),
                }

                if existing is None:
                    rows_by_section[code] = metadata
                elif existing != metadata:
                    raise RuntimeError(
                        f"Inconsistent metadata returned for section {code}."
                    )

                chunks_by_section[code].append(
                    {
                        "chunk_index": int(chunk_index),
                        "chunk_total": int(chunk_total),
                        "text": text,
                    }
                )

    finally:
        await dispose_engine()

    for code, chunks in chunks_by_section.items():
        chunks.sort(key=lambda item: item["chunk_index"])

        declared_totals = {item["chunk_total"] for item in chunks}
        if len(declared_totals) != 1:
            raise RuntimeError(
                f"{code}: inconsistent chunk_total values: "
                f"{sorted(declared_totals)}"
            )

        declared_total = next(iter(declared_totals))
        if declared_total != len(chunks):
            raise RuntimeError(
                f"{code}: declared chunk_total={declared_total}, "
                f"but database returned {len(chunks)} chunks."
            )

        expected_indices = list(range(len(chunks)))
        actual_indices = [item["chunk_index"] for item in chunks]
        if actual_indices != expected_indices:
            raise RuntimeError(
                f"{code}: non-contiguous chunk indices: {actual_indices}"
            )

        rows_by_section[code]["chunks"] = chunks

    return rows_by_section


async def main(count: int, seed: str, output_path: Path) -> None:
    if count < 1:
        raise SystemExit("--count must be at least 1.")
    if not seed.strip():
        raise SystemExit("--seed must not be empty.")

    if output_path.exists():
        raise SystemExit(
            f"Output already exists: {output_path}\n"
            "The holdout source sample is frozen. Do not overwrite it "
            "implicitly."
        )

    development_sections = load_development_sections(DEV_GOLD_PATH)
    substantive_sections = await load_substantive_sections()

    eligible_codes = sorted(
        code
        for code in substantive_sections
        if code not in development_sections
    )

    if len(eligible_codes) < count:
        raise SystemExit(
            f"Requested {count} holdout source sections, but only "
            f"{len(eligible_codes)} sections remain after excluding "
            "development gold sections."
        )

    ranked_codes = sorted(
        eligible_codes,
        key=lambda code: (selection_key(seed, code), code),
    )
    selected_codes = ranked_codes[:count]

    selected_sections = [
        {
            "selection_rank": rank,
            **substantive_sections[code],
        }
        for rank, code in enumerate(selected_codes, start=1)
    ]

    output = {
        "schema": "waypoint-holdout-source-sample-v1",
        "selection_method": (
            "SHA256(seed|section_code) ascending over substantive database "
            "sections after excluding development expected_sections"
        ),
        "seed": seed,
        "requested_count": count,
        "selected_count": len(selected_sections),
        "development_gold_sha256": sha256_file(DEV_GOLD_PATH),
        "development_gold_section_count": len(development_sections),
        "database_substantive_section_count": len(substantive_sections),
        "eligible_unseen_section_count": len(eligible_codes),
        "sections": selected_sections,
    }

    serialised = json.dumps(
        output,
        indent=2,
        ensure_ascii=False,
    ) + "\n"

    output_path.write_text(serialised, encoding="utf-8")

    # Re-read and verify that no development gold section was selected.
    verify = json.loads(output_path.read_text(encoding="utf-8"))
    verify_sections = verify.get("sections")

    if not isinstance(verify_sections, list):
        raise RuntimeError("Frozen holdout source artifact has no sections list.")

    verify_codes = [
        item.get("section_code")
        for item in verify_sections
        if isinstance(item, dict)
    ]

    if len(verify_codes) != count:
        raise RuntimeError(
            "Frozen holdout source artifact changed section count."
        )

    overlap = sorted(set(verify_codes) & development_sections)
    if overlap:
        raise RuntimeError(
            "Holdout source sample overlaps development gold sections: "
            + ", ".join(overlap)
        )

    if len(set(verify_codes)) != len(verify_codes):
        raise RuntimeError("Duplicate section codes in holdout source sample.")

    print("Waypoint holdout source freeze")
    print("=" * 30)
    print(f"Development gold:          {DEV_GOLD_PATH}")
    print(f"Output:                    {output_path}")
    print(f"Seed:                      {seed}")
    print()
    print(
        f"Substantive DB sections:   {len(substantive_sections)}"
    )
    print(
        f"Development gold sections: {len(development_sections)}"
    )
    print(
        f"Eligible unseen sections:  {len(eligible_codes)}"
    )
    print(
        f"Frozen holdout sections:   {len(selected_sections)}"
    )
    print()
    print("Selected sections")
    print("-" * 76)

    for item in selected_sections:
        print(
            f"{item['selection_rank']:>2}. "
            f"{item['section_code']:<10} "
            f"{item['title']}"
        )

    print()
    print(f"Development overlap:       none")
    print(f"Development gold SHA256:   {sha256_file(DEV_GOLD_PATH)}")
    print(f"Holdout source SHA256:     {sha256_file(output_path)}")
    print("Database writes:           NONE")
    print("Retrieval/model calls:     NONE")
    print("Holdout source freeze:     PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Freeze deterministic unseen corpus sections for holdout authoring."
        )
    )
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
    )
    parser.add_argument(
        "--seed",
        type=str,
        default=DEFAULT_SEED,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )
    args = parser.parse_args()

    asyncio.run(main(args.count, args.seed, args.output))