from pydantic import BaseModel


class QuoteData(BaseModel):
    ticker: str
    price: float
    change_pct: float
    volume: int
    volume_zscore: float
    timestamp: str


class NewsItem(BaseModel):
    title: str
    source: str
    url: str
    published_at: str
    sentiment_label: str | None = None
    sentiment_score: float | None = None
