"""
Train and save the IsolationForest anomaly model.
Run: python scripts/train_anomaly.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

from app.config import settings


def train():
    rng = np.random.default_rng(42)

    # Normal market data: [volume_zscore, price_change_pct, sentiment_intensity, keyword_spike, novelty]
    normal = rng.normal(loc=[0, 0, 0.3, 0.1, 0.5], scale=[0.8, 0.5, 0.2, 0.1, 0.2], size=(3000, 5))
    normal = np.clip(normal, -4, 4)

    # Inject known anomalies
    anomalies = rng.normal(loc=[3, 2, 0.8, 0.9, 0.8], scale=[0.5, 0.5, 0.1, 0.1, 0.1], size=(150, 5))

    X = np.vstack([normal, anomalies])

    model = IsolationForest(
        n_estimators=200,
        contamination=0.05,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X)

    model_path = Path(settings.anomaly_model_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, model_path)
    print(f"Model saved to {model_path}")

    # Quick sanity check
    normal_sample = np.array([[0.1, 0.2, 0.3, 0.0, 0.5]])
    anomaly_sample = np.array([[3.5, 2.5, 0.9, 1.0, 0.8]])
    print(f"Normal sample prediction: {model.predict(normal_sample)[0]} (expected 1)")
    print(f"Anomaly sample prediction: {model.predict(anomaly_sample)[0]} (expected -1)")


if __name__ == "__main__":
    train()
