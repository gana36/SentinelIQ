import json
from pathlib import Path

import numpy as np

from app.config import settings
from app.utils.logger import logger

_index = None
_metadata: list[dict] = []


def _load():
    global _index, _metadata
    if _index is not None:
        return

    import faiss

    idx_path = Path(settings.faiss_index_path)
    meta_path = Path(settings.faiss_metadata_path)

    if idx_path.exists() and meta_path.exists():
        _index = faiss.read_index(str(idx_path))
        _metadata = json.loads(meta_path.read_text())
        logger.info("faiss_loaded", vectors=_index.ntotal)
    else:
        logger.warning("faiss_index_not_found", path=str(idx_path), fallback="empty_index")
        _index = faiss.IndexFlatL2(1024)
        _metadata = []


def search(query_vector: np.ndarray, k: int = 3) -> list[dict]:
    _load()
    if _index.ntotal == 0:
        return []
    k = min(k, _index.ntotal)
    vec = query_vector.reshape(1, -1).astype(np.float32)
    distances, indices = _index.search(vec, k)
    results = []
    for dist, idx in zip(distances[0], indices[0]):
        if idx == -1:
            continue
        entry = dict(_metadata[idx])
        entry["similarity_score"] = float(1 / (1 + dist))
        results.append(entry)
    return results


def add(vector: np.ndarray, metadata: dict) -> None:
    _load()
    import faiss
    vec = vector.reshape(1, -1).astype(np.float32)
    _index.add(vec)
    _metadata.append(metadata)


def save() -> None:
    import faiss
    faiss.write_index(_index, settings.faiss_index_path)
    Path(settings.faiss_metadata_path).write_text(json.dumps(_metadata))
    logger.info("faiss_saved", vectors=_index.ntotal)
