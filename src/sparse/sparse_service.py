import asyncio
from fastembed import SparseTextEmbedding
from qdrant_client import models
from src.settings import Settings

_settings = Settings()

_model: SparseTextEmbedding = SparseTextEmbedding(
    model_name=_settings.sparse_model_name, cache_dir="/model"
)


async def calc_sparse_embedding(texts: list[str]) -> list[models.SparseVector]:
    # Verschiebe die Embedding-Berechnung in einen separaten Thread
    embeddings = await asyncio.to_thread(_compute_embedding, texts)

    sparse_vectors = []

    for emb in embeddings:
        if hasattr(emb, "indices") and hasattr(emb, "values"):
            sparse_vectors.append(
                models.SparseVector(
                    indices=emb.indices.tolist(), values=emb.values.tolist()
                )
            )

    return sparse_vectors


def _compute_embedding(texts: str):
    return list(_model.embed(texts))
