import hashlib


def mock_analyze(text: str) -> dict:
    """Deterministic mock — same text always returns same result."""
    h = int(hashlib.md5(text.encode()).hexdigest(), 16)
    labels = ["positive", "negative", "neutral"]
    label = labels[h % 3]
    confidence = 0.55 + (h % 40) / 100  # 0.55–0.95

    scores = {"positive": 0.1, "negative": 0.1, "neutral": 0.1}
    scores[label] = confidence
    remaining = (1 - confidence) / 2
    for k in scores:
        if k != label:
            scores[k] = remaining

    return {
        "label": label,
        "confidence": confidence,
        "scores": scores,
        "intensity": scores["positive"] - scores["negative"],
    }
