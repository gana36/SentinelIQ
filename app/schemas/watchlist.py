import uuid
from datetime import datetime

from pydantic import BaseModel


class WatchlistItemIn(BaseModel):
    ticker: str


class WatchlistItemOut(BaseModel):
    id: uuid.UUID
    ticker: str
    added_at: datetime

    model_config = {"from_attributes": True}
