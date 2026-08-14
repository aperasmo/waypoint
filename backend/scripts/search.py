"""Ad hoc retrieval check. Usage: uv run python -m scripts.search "your question" """

import asyncio
import sys

from app.db.session import dispose_engine, get_session_factory
from app.ingestion.embedder import OpenAIEmbedder
from app.retrieval.retriever import retrieve


async def main(query: str) -> None:
    factory = get_session_factory()
    embedder = OpenAIEmbedder()

    async with factory() as session:
        results = await retrieve(session, query, embedder, limit=5)

    print(f"\nQuery: {query}\n")
    if not results:
        print("No results.")
    for r in results:
        legs = f"v={r.vector_rank or '-':>2} t={r.text_rank or '-':>2}"
        both = " BOTH" if r.matched_both else ""
        print(f"{r.score:.4f}  {legs}{both}  {r.section_code}")
        print(f"        {r.title[:70]}")
        print(f"        {r.text[:120].replace(chr(10), ' ')}...")
        print()

    await dispose_engine()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: uv run python -m scripts.search "your question"')
        sys.exit(1)
    asyncio.run(main(" ".join(sys.argv[1:])))