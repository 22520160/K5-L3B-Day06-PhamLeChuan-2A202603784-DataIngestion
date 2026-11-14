from sentence_transformers import SentenceTransformer


class MyEmbedder:
    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimensions = self.model.get_sentence_embedding_dimension()

        if self.dimensions is None:
            raise RuntimeError("Could not determine embedding dimensions")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []

        vectors = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return vectors.tolist()

    def embed_query(self, question: str) -> list[float]:
        vectors = self.model.encode(
            [question],
            normalize_embeddings=True,
            show_progress_bar=False,
        )

        return vectors[0].tolist()