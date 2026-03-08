import asyncio
import json

import numpy as np

from app.config import settings
from app.utils.logger import logger


async def embed_text(text: str) -> np.ndarray:
    """Return 1024-dim embedding vector using Amazon Nova 2 Multimodal Embeddings."""
    if settings.mock_mode:
        return _mock_embed(text)

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _call_bedrock, text)


def _call_bedrock(text: str) -> np.ndarray:
    from app.services.bedrock_client import get_bedrock_client
    client = get_bedrock_client()
    response = client.invoke_model(
        modelId=settings.bedrock_embedding_model_id,
        body=json.dumps({
            "taskType": "SINGLE_EMBEDDING",
            "singleEmbeddingParams": {
                "embeddingPurpose": "GENERIC_INDEX",
                "embeddingDimension": 1024,
                "text": {
                    "truncationMode": "END",
                    "value": text[:8192],
                },
            },
        }),
        contentType="application/json",
        accept="application/json",
    )
    body = json.loads(response["body"].read())
    return np.array(body["embeddings"][0]["embedding"], dtype=np.float32)


def _mock_embed(text: str) -> np.ndarray:
    """Deterministic pseudo-embedding based on text hash."""
    import hashlib
    seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
    rng = np.random.default_rng(seed)
    vec = rng.normal(size=1024).astype(np.float32)
    return vec / np.linalg.norm(vec)
