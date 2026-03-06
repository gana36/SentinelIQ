# SentinelIQ — Complete System Workflow

## What Is This?

SentinelIQ is an **Autonomous Market Intelligence Assistant** that:
1. Watches the internet (Reddit, news, market data, SEC filings) for unusual signals
2. Runs ML models to detect if something is actually anomalous
3. Sends the anomaly to Amazon Nova to generate a human-readable market analysis
4. Delivers a structured **Action Card** alert to the right users in real-time via WebSocket

No auto-trading. No price predictions. Just fast, explainable intelligence.

---

## Big Picture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA SOURCES                                 │
│  Reddit  │  NewsAPI  │  Polygon.io  │  SEC EDGAR  │  Mock (demo)   │
└────────────────────────────┬────────────────────────────────────────┘
                             │ RawSignal objects
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    INGESTION PIPELINE                               │
│         asyncio.Queue (max 500) — one producer per source          │
└────────────────────────────┬────────────────────────────────────────┘
                             │ one asyncio.Task per signal
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   5-AGENT PIPELINE                                  │
│  Agent 1 → Agent 2 → Agent 3 → Agent 4 → Agent 5                  │
│  (short-circuits if signal doesn't pass quality gates)             │
└────────────────────────────┬────────────────────────────────────────┘
                             │ ActionCard
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    ALERT DISPATCH                                   │
│     PostgreSQL  ──  Redis pub/sub  ──  WebSocket push              │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
                    📱 User's browser / app
```

---

## Step-by-Step Signal Flow

### Step 1 — A Signal Is Born

A raw signal enters the system from one of these sources:

| Source | What it watches | How often |
|--------|----------------|-----------|
| **Reddit** (`asyncpraw`) | r/stocks, r/wallstreetbets, r/investing | Real-time stream |
| **NewsAPI** | Breaking financial headlines | Every 60 seconds |
| **Polygon.io** | Price & volume for watchlisted tickers | Every 30 seconds |
| **SEC EDGAR** | 8-K regulatory filings via RSS | Every 2 minutes |
| **Mock source** | 5 scripted demo events from `data/demo_events.json` | Every 30 seconds |

Every source normalizes its output into the same `RawSignal` shape:

```python
RawSignal(
    signal_id = "uuid",
    source    = "reddit" | "news" | "market" | "sec" | "mock",
    ticker    = "TSLA",          # resolved from text, or None
    raw_text  = "Tesla just crushed earnings...",
    timestamp = datetime,
    metadata  = { "url": "...", "volume_zscore": 2.4, ... }
)
```

---

### Step 2 — Into the Queue

Every `RawSignal` is dropped into an `asyncio.Queue` (capped at 500).

- A **consumer loop** reads signals as fast as they arrive
- Each signal gets its own `asyncio.create_task()` — signals are processed **concurrently**, not sequentially
- The raw signal is also pushed to Redis (`signals:live` list, capped at 200) so the frontend can show a live feed

---

### Step 3 — Agent 1: Signal Scout

**What it does:** Decides whether this signal is interesting enough to investigate.

**ML: Sentiment Classification (FinBERT)**
- Loads `ProsusAI/finbert` from HuggingFace (runs on CPU in a threadpool executor)
- Classifies the raw text as `positive`, `negative`, or `neutral`
- Returns a confidence score (0–1) and intensity (positive score minus negative score)

```
Input:  "$TSLA just crushed Q4 earnings! EPS beat by 30%..."
Output: { label: "positive", confidence: 0.94, intensity: 0.88 }
```

**ML: Anomaly Detection (IsolationForest)**
- Builds a 5-dimensional feature vector from the signal:
  - `volume_zscore` — how unusual is today's trading volume?
  - `price_change_pct` — how much did the price move?
  - `sentiment_intensity` — how extreme is the sentiment score?
  - `keyword_spike` — does text contain "breaking", "crash", "surge", etc.?
  - `novelty` — default 0.5 (can be enhanced with dedup scoring)
- Runs through a pre-trained `IsolationForest` model
- Returns `is_anomaly: true/false` and an `anomaly_score` (more negative = more unusual)

**Short-circuit:** If `is_anomaly = false`, the signal is dropped here. ~70% of signals are filtered out.

---

### Step 4 — Agent 2: Credibility Checker

**What it does:** Scores how trustworthy the source is.

**Source scoring:**
```
SEC EDGAR filing  → 0.98
Reuters / Bloomberg → 0.90–0.95
CNBC / WSJ        → 0.85–0.92
NewsAPI (generic)  → 0.70
Market data       → 0.80
Reddit            → 0.45
Mock/Unknown      → 0.30–0.75
```

**Multi-source bonus:** Checks Redis for how many independent sources reported the same ticker in the last 5 minutes. Each additional source adds +0.20 (up to +0.30).

**Short-circuit:** If `credibility_score < 0.3`, the signal is dropped.

---

### Step 5 — Agent 3: Market Impact Analyst (Nova Lite)

**What it does:** Sends everything to Amazon Nova Lite and asks for structured analysis.

The agent builds a prompt like this:

```
SYSTEM: You are a financial intelligence analyst. Respond ONLY with valid JSON.

USER: Signal details:
- Ticker: TSLA
- Sentiment: positive (confidence: 94%)
- Anomaly score: -0.31 (is_anomaly: True)
- Source: reddit
- Credibility: 75%
- Text: "$TSLA just crushed Q4 earnings! EPS beat by 30%..."

Produce this JSON:
{
  "event_summary": "...",
  "affected_tickers": ["TSLA"],
  "primary_driver": "...",
  "sector_impact": "...",
  "confidence_level": 0.0–1.0,
  "risk_factors": ["..."],
  "time_horizon": "intraday | short-term | long-term",
  "recommended_actions": ["Monitor", "Review position"]
}
```

Nova returns a structured JSON response that gets stored in `context["nova_analysis"]`.

---

### Step 6 — Agent 4: Personalization Agent

**What it does:** Finds which users actually care about this ticker.

- Loads all user watchlists from PostgreSQL (Redis-cached for 60 seconds to avoid DB hammering)
- Filters to users who have the affected ticker in their watchlist
- Also applies `alert_sensitivity` filter — if the user requires high confidence (`sensitivity = 0.8`) and Nova only returned `confidence_level = 0.6`, the alert is skipped for that user

**Short-circuit:** If no users match, the pipeline stops here.

---

### Step 7 — Agent 5: Action Composer

**What it does:** Builds the final `ActionCard` — the rich payload delivered to the user.

- Calls **Nova Multimodal Embeddings** (via Bedrock) on the signal text → gets a 1024-dimensional vector
- Searches the **FAISS index** for the 3 most similar historical market events
- Assembles everything into an `ActionCard`:

```json
{
  "alert_id": "uuid",
  "ticker": "TSLA",
  "event_summary": "Tesla reports Q4 earnings beat of 30% on EPS...",
  "sentiment": {
    "label": "positive",
    "confidence": 0.94,
    "intensity": 0.88
  },
  "anomaly": {
    "is_anomaly": true,
    "anomaly_score": -0.31
  },
  "nova_analysis": {
    "event_summary": "...",
    "affected_tickers": ["TSLA"],
    "primary_driver": "Earnings beat significantly above consensus",
    "sector_impact": "Positive for EV sector broadly",
    "confidence_level": 0.87,
    "risk_factors": ["Short-term profit taking", "Macro headwinds"],
    "time_horizon": "intraday",
    "recommended_actions": ["Monitor closely", "Review position size"]
  },
  "similar_events": [
    {
      "date": "2023-07-19",
      "ticker": "TSLA",
      "event": "Tesla beats Q2 delivery estimates; price cuts drive volume",
      "outcome": "Stock surged 10% on earnings day",
      "similarity_score": 0.91
    }
  ],
  "credibility_score": 0.75,
  "source_links": ["https://reddit.com/r/stocks/..."],
  "timestamp": "2026-03-04T16:45:00Z",
  "voice_ready": true
}
```

---

### Step 8 — Alert Dispatch

The `ActionCard` is delivered to each target user through three parallel channels:

```
ActionCard
    │
    ├─► PostgreSQL: INSERT INTO alerts (persisted for history)
    │
    ├─► Redis PUBLISH "alerts:{user_id}" (decoupled message bus)
    │         │
    │         └─► WebSocket handler subscribes to this channel
    │
    └─► WebSocket direct push (if user is currently connected)
```

The Redis pub/sub layer is the key architectural decision: the agent pipeline runs as a **background asyncio task**, completely separate from the HTTP request context. Redis bridges the two so alerts generated in the background reach connected browser clients in real-time.

---

### Step 9 — Voice Explanation (Nova Sonic)

After receiving an alert, the user can ask:

> "Why is Tesla spiking right now?"

**`POST /api/v1/voice/explain`** receives the `alert_id` + question, looks up the stored ActionCard, builds a conversational prompt from the Nova analysis, and calls **Amazon Nova Sonic** to return a synthesized audio response.

---

## API Surface

```
POST   /api/v1/auth/register           Create account
POST   /api/v1/auth/login              Get JWT token

GET    /api/v1/users/me                Profile
PATCH  /api/v1/users/me/preferences    Update risk tolerance & alert sensitivity

GET    /api/v1/watchlist               List tickers
POST   /api/v1/watchlist               Add ticker
DELETE /api/v1/watchlist/{ticker}      Remove ticker

GET    /api/v1/alerts                  Paginated alert history
GET    /api/v1/alerts/{id}             Full ActionCard
PATCH  /api/v1/alerts/{id}/read        Mark as read

GET    /api/v1/signals/live            Last 50 raw signals (Redis)

GET    /api/v1/market/quote/{ticker}   Live price + volume
GET    /api/v1/market/news             Recent financial news

POST   /api/v1/voice/explain           Nova Sonic voice response

WS     /api/v1/ws/alerts?token=<jwt>   Real-time alert stream

POST   /api/v1/dev/inject-signal       [Demo only] Inject a scripted event
```

---

## MOCK_MODE

When `MOCK_MODE=true` in `.env`, every real integration is swapped for a deterministic mock:

| Real | Mock |
|------|------|
| FinBERT (HuggingFace) | MD5-hash-based deterministic label |
| IsolationForest (.joblib) | Hash-based, ~30% anomaly rate |
| Nova Lite (Bedrock) | Pre-written template response |
| Nova Sonic (Bedrock) | Text transcript only, no audio |
| Nova Embeddings | Random unit vector seeded by text hash |
| FAISS search | 3 hardcoded historical events |
| Reddit/News/Market/SEC streams | 5 scripted events from `data/demo_events.json`, fires every 30s |

This means the **entire system works end-to-end for a demo with just PostgreSQL and Redis** — no AWS account or API keys needed.

---

## Data Flow Diagram (Detailed)

```
Reddit ──────────────────────┐
NewsAPI ──────────────────── ├──► asyncio.Queue[RawSignal]
Polygon.io ───────────────── │         │
SEC EDGAR ────────────────── │         │  create_task() per signal
Mock (demo) ─────────────────┘         │
                                        ▼
                              ┌─────────────────┐
                              │  SignalScout     │  FinBERT + IsoForest
                              │  (Agent 1)       │  ticker resolution
                              └────────┬────────┘
                                       │ is_anomaly? ──NO──► drop
                                       ▼
                              ┌─────────────────┐
                              │  Credibility     │  source whitelist
                              │  Checker (Ag 2)  │  Redis multi-source
                              └────────┬────────┘
                                       │ score < 0.3? ──► drop
                                       ▼
                              ┌─────────────────┐
                              │  MarketImpact    │  Nova Lite
                              │  Analyst (Ag 3)  │  → structured JSON
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │  Personalization │  watchlist match
                              │  Agent (Ag 4)    │  sensitivity filter
                              └────────┬────────┘
                                       │ no users? ──► drop
                                       ▼
                              ┌─────────────────┐
                              │  ActionComposer  │  Nova Embeddings
                              │  (Agent 5)       │  FAISS similarity
                              └────────┬────────┘
                                       │ ActionCard
                                       ▼
                         ┌─────────────────────────┐
                         │    AlertDispatcher       │
                         │  DB + Redis + WebSocket  │
                         └─────────────────────────┘
                                       │
                              ┌────────┴────────┐
                              ▼                  ▼
                         PostgreSQL         Redis pub/sub
                         (persisted)            │
                                           WebSocket
                                           (real-time)
                                               │
                                          User Browser
```

---

## File Structure at a Glance

```
app/
├── main.py              FastAPI app + startup/shutdown lifecycle
├── config.py            All settings, MOCK_MODE flag
├── dependencies.py      JWT auth dependency
│
├── api/v1/
│   ├── auth.py          POST /register, /login
│   ├── users.py         GET/PATCH /users/me
│   ├── watchlist.py     CRUD watchlist
│   ├── alerts.py        GET alert history
│   ├── signals.py       GET live signals
│   ├── market.py        GET quotes + news
│   ├── voice.py         POST Nova Sonic
│   ├── ws.py            WebSocket endpoint
│   └── dev.py           POST inject-signal (demo)
│
├── agents/
│   ├── orchestrator.py  Sequential chain runner
│   ├── signal_scout.py  Agent 1
│   ├── credibility_checker.py  Agent 2
│   ├── market_impact_analyst.py  Agent 3
│   ├── personalization_agent.py  Agent 4
│   └── action_composer.py  Agent 5
│
├── ml/
│   ├── sentiment/finbert_classifier.py   HuggingFace FinBERT
│   ├── anomaly/isolation_forest.py       sklearn IsolationForest
│   └── embeddings/nova_embeddings.py     Bedrock embeddings
│                 faiss_store.py          FAISS IndexFlatL2
│
├── ingestion/
│   ├── pipeline.py      asyncio.Queue coordinator
│   ├── normalizer.py    RawSignal dataclass
│   └── sources/         reddit, news, market, sec, mock
│
└── services/
    ├── nova_reasoning.py   Bedrock Converse API call
    ├── nova_sonic.py       Bedrock voice synthesis
    ├── cache.py            Redis helpers
    ├── alert_dispatcher.py DB + Redis + WS delivery
    └── websocket_manager.py Per-user WS connections
```
