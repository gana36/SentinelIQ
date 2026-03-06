MOCK_SIMILAR_EVENTS = [
    {
        "date": "2023-02-08",
        "ticker": "GOOGL",
        "event": "Google announces Bard AI chatbot amid ChatGPT competition fears",
        "outcome": "Stock dropped 9% initially, recovered within 2 weeks",
        "sentiment": "negative",
        "similarity_score": 0.87,
    },
    {
        "date": "2022-10-27",
        "ticker": "META",
        "event": "Meta reports Q3 earnings miss; Zuckerberg doubles down on metaverse",
        "outcome": "Stock fell 25% in after-hours trading",
        "sentiment": "negative",
        "similarity_score": 0.79,
    },
    {
        "date": "2023-07-19",
        "ticker": "TSLA",
        "event": "Tesla beats Q2 delivery estimates; price cuts drive volume",
        "outcome": "Stock surged 10% on earnings day",
        "sentiment": "positive",
        "similarity_score": 0.72,
    },
]


def mock_search(query_text: str, k: int = 3) -> list[dict]:
    return MOCK_SIMILAR_EVENTS[:k]
