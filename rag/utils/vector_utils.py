from pathlib import Path


def load_faiss_database(index_path, embedding_dimension):
    """Load an existing FAISS index from disk, or create a new local index."""
    import faiss
    import numpy as np
    resolved_path = Path(index_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)

    if resolved_path.exists():
        loaded_index = faiss.read_index(str(resolved_path))
        if loaded_index.d != embedding_dimension:
            raise ValueError(
                f'Existing FAISS index dimension ({loaded_index.d}) does not match '
                f'current embedding dimension ({embedding_dimension}).'
            )
        if isinstance(loaded_index, faiss.IndexIDMap2):
            return loaded_index

        wrapped_index = faiss.IndexIDMap2(loaded_index)
        return wrapped_index

    base_index = faiss.IndexFlatIP(embedding_dimension)
    return faiss.IndexIDMap2(base_index)


def save_faiss_database(index, index_path) -> None:
    """Persist FAISS index state locally for durable retrieval across restarts."""
    import faiss
    resolved_path = Path(index_path)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(resolved_path))


def similarity_search(index, query_embedding, top_k: int = 5) -> list[dict]:
    """Run vector similarity search and return ids/scores in descending rank order."""
    if query_embedding.ndim != 2:
        raise ValueError('query_embedding must be a 2D numpy array shaped (1, dimension).')

    if top_k <= 0 or index.ntotal == 0:
        return []

    scores, indices = index.search(query_embedding.astype('float32'), top_k)
    ranked_hits: list[dict] = []

    for vector_id, score in zip(indices[0], scores[0], strict=True):
        # FAISS returns -1 when fewer than top_k records are available.
        if int(vector_id) < 0:
            continue
        ranked_hits.append({'vector_id': int(vector_id), 'score': float(score)})

    return ranked_hits
