import hashlib


def mock_score(features: list[float]) -> dict:
    """Deterministic mock anomaly scorer."""
    key = str(features)
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    # Make ~30% of signals anomalous for demo interest
    is_anomaly = (h % 10) < 3
    score = -0.25 if is_anomaly else 0.15
    return {
        "is_anomaly": is_anomaly,
        "anomaly_score": score,
        "threshold": -0.1,
    }
