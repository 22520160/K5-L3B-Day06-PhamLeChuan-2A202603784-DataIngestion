import json
import os

from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .ingestion import load_pdf
from .store import PgVectorStore
from .evaluation import evaluate_query, summarize

def build_page_metadata() -> dict[int, dict[str, str]]:
    metadata: dict[int, dict[str, str]] = {}

    def add_section(
        start_page: int,
        end_page: int,
        section: str,
        category: str | None = None,
    ) -> None:
        for page in range(start_page, end_page + 1):
            metadata[page] = {"section": section}

            if category:
                metadata[page]["category"] = category

    add_section(1, 8, "Front Matter")          
    add_section(9, 21, "Executive Summary")
    add_section(22, 32, "Energy", "Energy")
    add_section(33, 46, "Agriculture", "Agriculture")
    add_section(47, 48, "Fertilizers", "Fertilizers")
    add_section(49, 55, "Metals and minerals", "Metals and minerals")
    add_section(56, 67, "Special Focus")       
    add_section(68, 70, "References")          

    return metadata

def embed_chunks(embedder: MyEmbedder, chunks: list) -> list[list[float]]:
    vectors: list[list[float]] = []
    batch_size = 32

    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        vectors.extend(embedder.embed_documents([chunk.text for chunk in batch]))
        print(f"Embedded {min(start + batch_size, len(chunks))}/{len(chunks)}")
        
    return vectors


def main() -> None:
    load_dotenv()

    database_url = os.getenv("DATABASE_URL")
    model_name = os.getenv("EMBEDDING_MODEL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    if not model_name:
        raise RuntimeError("EMBEDDING_MODEL is not configured")

    pdf_path = Path("data/book.pdf")
    page_metadata = build_page_metadata()

    pages = load_pdf(pdf_path, "book", str(pdf_path), page_metadata=page_metadata,)

    content_pages = [page for page in pages if page.text]

    if len(content_pages) < 30:
        raise ValueError(
            f"Need at least 30 content pages, got {len(content_pages)}"
        )

    chunks_a = [
        chunk
        for page in content_pages
        for chunk in fixed_size(page, size=500, overlap=50)
    ]

    chunks_b = [
        chunk
        for page in content_pages
        for chunk in by_paragraph(page, max_size=1200)
    ]

    print(f"Content pages: {len(content_pages)}")
    print(f"Strategy A chunks: {len(chunks_a)}")
    print(f"Strategy B chunks: {len(chunks_b)}")

    embedder = MyEmbedder(model_name)

    print("Embedding strategy A...")
    vectors_a = embed_chunks(embedder, chunks_a)

    print("Embedding strategy B...")
    vectors_b = embed_chunks(embedder, chunks_b)

    if embedder.dimensions is None:
        raise RuntimeError("Embedding dimensions were not initialized")

    store = PgVectorStore(database_url, embedder.dimensions)
    store.create_schema()

    print("Saving strategy A...")
    store.upsert("A_fixed", chunks_a, vectors_a)

    print("Saving strategy B...")
    store.upsert("B_paragraph", chunks_b, vectors_b)

    print("Saving strategy C...")
    store.upsert("C_paragraph_filter", chunks_b, vectors_b)

    benchmark_path = Path("data/benchmark.json")
    questions = json.loads(benchmark_path.read_text(encoding="utf-8"))

    strategy_names = [
        "A_fixed",
        "B_paragraph",
        "C_paragraph_filter",
    ]

    traces = []

    for strategy in strategy_names:
        print(f"Evaluating {strategy}...")

        for question in questions:
            query_vector = embedder.embed_query(question["question"])

            filters = None
            if strategy == "C_paragraph_filter":
                filters = question.get("filter") or None

            hits = store.search(
                strategy=strategy,
                query_vector=query_vector,
                top_k=3,
                filters=filters,
            )

            evaluation = evaluate_query(question, hits)

            traces.append(
                {
                    "strategy": strategy,
                    "question": question,
                    "filters": filters,
                    "hits": hits,
                    **evaluation,
                }
            )

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    (results_dir / "traces.json").write_text(
        json.dumps(traces, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    (results_dir / "metrics.json").write_text(
        json.dumps(summarize(traces), indent=2),
        encoding="utf-8",
    )

    print("Benchmark completed successfully")

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    summary = {
        "document": str(pdf_path),
        "content_pages": len(content_pages),
        "embedding_model": model_name,
        "embedding_dimensions": embedder.dimensions,
        "strategies": {
            "A_fixed": len(chunks_a),
            "B_paragraph": len(chunks_b),
            "C_paragraph_filter": len(chunks_b),
        },
    }

    (results_dir / "ingestion_summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    print("Ingestion completed successfully")


if __name__ == "__main__":
    main()
