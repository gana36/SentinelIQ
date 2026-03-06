import re

# Common company name → ticker mappings
_ENTITY_MAP = {
    "tesla": "TSLA",
    "apple": "AAPL",
    "microsoft": "MSFT",
    "nvidia": "NVDA",
    "amazon": "AMZN",
    "google": "GOOGL",
    "alphabet": "GOOGL",
    "meta": "META",
    "facebook": "META",
    "netflix": "NFLX",
    "openai": "MSFT",  # proxy
    "fed": "SPY",
    "federal reserve": "SPY",
    "s&p": "SPY",
    "sp500": "SPY",
    "bitcoin": "COIN",
}

_CASHTAG_PATTERN = re.compile(r"\$([A-Z]{1,5})\b")


def resolve_ticker(text: str) -> str | None:
    """Extract ticker from text. Returns first match or None."""
    # 1. Cashtag ($TSLA)
    matches = _CASHTAG_PATTERN.findall(text)
    if matches:
        return matches[0].upper()

    # 2. Entity name lookup
    lower = text.lower()
    for name, ticker in _ENTITY_MAP.items():
        if name in lower:
            return ticker

    return None
