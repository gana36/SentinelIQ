import asyncio
from pathlib import Path

import joblib
import numpy as np

from app.config import settings
from app.utils.logger import logger


class AnomalyDetector:
    def __init__(self):
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        path = Path(settings.anomaly_model_path)
        if path.exists():
            self._model = joblib.load(path)
            logger.info("anomaly_model_loaded", path=str(path))
        else:
            logger.warning("anomaly_model_not_found", path=str(path), fallback="training_new")
            self._train_default()

    def _train_default(self):
        from sklearn.ensemble import IsolationForest
        rng = np.random.default_rng(42)
        # Synthetic "normal" market data: [volume_zscore, price_change_pct, tweet_freq_delta, keyword_spike, sentiment_delta]
        normal = rng.normal(loc=0, scale=1, size=(2000, 5))
        normal = np.clip(normal, -3, 3)
        self._model = IsolationForest(n_estimators=100, contamination=0.05, random_state=42)
        self._model.fit(normal)
        logger.info("anomaly_model_trained_in_memory")

    async def score(self, features: list[float]) -> dict:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._score, features)

    def _score(self, features: list[float]) -> dict:
        self._load()
        arr = np.array(features, dtype=float).reshape(1, -1)
        score = float(self._model.decision_function(arr)[0])
        is_anomaly = bool(self._model.predict(arr)[0] == -1)
        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": score,
            "threshold": -0.1,
        }


_detector: AnomalyDetector | None = None


def get_anomaly_detector() -> AnomalyDetector:
    global _detector
    if _detector is None:
        _detector = AnomalyDetector()
    return _detector
