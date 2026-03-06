import asyncio
from functools import lru_cache

from app.utils.logger import logger


class FinBERTClassifier:
    def __init__(self):
        self._pipeline = None

    def _load(self):
        if self._pipeline is None:
            from transformers import pipeline
            logger.info("loading_finbert")
            self._pipeline = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                return_all_scores=True,
                device=-1,  # CPU
            )
            logger.info("finbert_loaded")

    async def analyze(self, text: str) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._run, text)

    def _run(self, text: str) -> dict:
        self._load()
        scores = self._pipeline(text[:512])[0]
        label_map = {s["label"].lower(): s["score"] for s in scores}
        dominant = max(label_map, key=label_map.get)
        return {
            "label": dominant,
            "confidence": label_map[dominant],
            "scores": label_map,
            "intensity": label_map.get("positive", 0) - label_map.get("negative", 0),
        }


@lru_cache(maxsize=1)
def get_finbert() -> FinBERTClassifier:
    return FinBERTClassifier()
