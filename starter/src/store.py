import json
import math
import re
from typing import Any

import psycopg

from .models import Chunk


def _vector_literal(vector: list[float]) -> str:
    if not vector:
        raise ValueError("Vector cannot be empty")

    if not all(math.isfinite(value) for value in vector):
        raise ValueError("Vector contains a non-finite value")

    return "[" + ",".join(repr(float(value)) for value in vector) + "]"


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than zero")

        self.database_url = database_url
        self.dimensions = dimensions

    def create_schema(self) -> None:
        sql = f"""
        CREATE TABLE IF NOT EXISTS day6_chunks (
            strategy TEXT NOT NULL,
            chunk_id TEXT NOT NULL,
            document_id TEXT NOT NULL,
            source TEXT NOT NULL,
            page INTEGER NOT NULL,
            text TEXT NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
            embedding vector({self.dimensions}) NOT NULL,
            PRIMARY KEY (strategy, chunk_id)
        )
        """

        with psycopg.connect(self.database_url) as connection:
            connection.execute(sql)
            connection.commit()

    def upsert(
        self,
        strategy: str,
        chunks: list[Chunk],
        vectors: list[list[float]],
    ) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")

        for vector in vectors:
            if len(vector) != self.dimensions:
                raise ValueError(
                    f"Expected {self.dimensions} dimensions, got {len(vector)}"
                )

        self.create_schema()

        insert_sql = """
        INSERT INTO day6_chunks (
            strategy, chunk_id, document_id, source, page,
            text, metadata, embedding
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector
        )
        ON CONFLICT (strategy, chunk_id)
        DO UPDATE SET
            document_id = EXCLUDED.document_id,
            source = EXCLUDED.source,
            page = EXCLUDED.page,
            text = EXCLUDED.text,
            metadata = EXCLUDED.metadata,
            embedding = EXCLUDED.embedding
        """

        with psycopg.connect(self.database_url) as connection:
            for chunk, vector in zip(chunks, vectors):
                connection.execute(
                    insert_sql,
                    (
                        strategy,
                        chunk.chunk_id,
                        chunk.document_id,
                        chunk.source,
                        chunk.page,
                        chunk.text,
                        json.dumps(chunk.metadata),
                        _vector_literal(vector),
                    ),
                )
            connection.commit()

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if len(query_vector) != self.dimensions:
            raise ValueError(
                f"Expected {self.dimensions} dimensions, got {len(query_vector)}"
            )

        if top_k <= 0:
            raise ValueError("top_k must be greater than zero")

        conditions = ["strategy = %s"]
        parameters: list[Any] = [strategy]

        for key, value in (filters or {}).items():
            if not re.fullmatch(r"[A-Za-z0-9_]+", key):
                raise ValueError(f"Invalid metadata filter key: {key}")

            conditions.append("metadata ->> %s = %s")
            parameters.extend([key, str(value)])

        where_clause = " AND ".join(conditions)

        sql = f"""
        SELECT
            chunk_id,
            document_id,
            source,
            page,
            text,
            metadata,
            1 - (embedding <=> %s::vector) AS score
        FROM day6_chunks
        WHERE {where_clause}
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """

        vector = _vector_literal(query_vector)
        parameters = [vector, *parameters, vector, top_k]

        with psycopg.connect(self.database_url) as connection:
            rows = connection.execute(sql, parameters).fetchall()

        return [
            {
                "chunk_id": row[0],
                "document_id": row[1],
                "source": row[2],
                "page": row[3],
                "text": row[4],
                "metadata": row[5],
                "score": float(row[6]),
            }
            for row in rows
        ]