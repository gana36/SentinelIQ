<div align="center">

# SentinelIQ
### Autonomous Market Intelligence Assistant

*The market never sleeps. Neither does SentinelIQ.*

![AWS](https://img.shields.io/badge/AWS-Bedrock-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![Nova](https://img.shields.io/badge/Amazon-Nova-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)

**[Live Demo](https://dev.d298cyp4lj4l0k.amplifyapp.com/) · [API Docs](https://xma6vfhzzb.us-east-1.awsapprunner.com/docs)**

</div>

---

## What is SentinelIQ?

SentinelIQ watches financial markets 24/7 — ingesting news, social signals, and SEC filings — then uses **Amazon Nova** to autonomously decide what's noise and what's a genuine market event worth acting on.

Unlike rule-based alert systems, SentinelIQ uses **true agentic AI**: Nova Lite receives a raw signal and a set of tools, then decides on its own which tools to call, in what order, and whether the signal deserves an alert. Most signals get dropped. Only genuine anomalies reach users.

---

## System Architecture

```
╔══════════════════════════════════════════════════════════════════════╗
║                        LIVE DATA SOURCES                            ║
║                                                                      ║
║   NewsAPI         Polygon.io        Twitter/X         Reddit        ║
║   (financial       (market data,     (social           (WSB,         ║
║    headlines)       price & vol)      signals)          r/stocks)    ║
╚══════════════╦═══════════════════════════════════════════════════════╝
               ║  Raw signals → asyncio.Queue
               ▼
╔══════════════════════════════════════════════════════════════════════╗
║                       AGENT ORCHESTRATOR                            ║
║                                                                      ║
║   Signal arrives → Nova Lite receives signal + tool definitions     ║
║                                                                      ║
║   ┌─────────────────────────────────────────────────────────────┐   ║
║   │              Nova Lite Agentic Loop (max 10 rounds)         │   ║
║   │                                                             │   ║
║   │  Round 1 ──► run_sentiment ──────► FinBERT classifier       │   ║
║   │  Round 2 ──► run_anomaly_detection ► IsolationForest        │   ║
║   │  Round 3 ──► check_credibility ──► Source trust score       │   ║
║   │  Round 4 ──► find_similar_events ► FAISS vector search      │   ║
║   │  Round 5 ──► get_target_users ───► Watchlist matching       │   ║
║   │  Round 6 ──► compose_alert ──────► Build ActionCard         │   ║
║   │                    │                                         │   ║
║   │              Nova decides. If signal is noise → DROP         │   ║
║   └────────────────────┼────────────────────────────────────────┘   ║
╚════════════════════════╬═════════════════════════════════════════════╝
                         ║  ActionCard (only genuine anomalies)
                         ▼
╔══════════════════════════════════════════════════════════════════════╗
║                        ALERT DISPATCHER                             ║
║                                                                      ║
║   ┌──────────────┐  ┌─────────────────┐  ┌───────────────────────┐ ║
║   │  PostgreSQL  │  │  Redis pub/sub  │  │    WebSocket push     │ ║
║   │  (persisted) │  │  (fan-out)      │  │    (real-time UI)     │ ║
║   └──────────────┘  └─────────────────┘  └───────────────────────┘ ║
║                                                                      ║
║   Email (parallel enrichment):                                      ║
║     ├── TradingView chart  ──────── Nova Act (browser automation)   ║
║     └── SEC EDGAR filings  ──────── Nova Act → Nova Lite            ║
╚══════════════════════════════════════════════════════════════════════╝
                         ║
                         ▼
╔══════════════════════════════════════════════════════════════════════╗
║                            USER                                     ║
║                                                                      ║
║   Real-time alert in browser       Rich HTML email                  ║
║   Watchlist-filtered alerts        TradingView + EDGAR cards        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Amazon Nova — 4 Services, One Pipeline

```
┌─────────────────────────────────────────────────────────────────────┐
│                      NOVA SERVICES IN USE                           │
├─────────────────────┬───────────────────────────────────────────────┤
│  Nova Lite           │  Agentic orchestrator — given tools + signal, │
│  (Bedrock Converse) │  decides tool sequence, drops noise, composes  │
│                     │  alerts. Runs up to 10 agentic rounds.         │
├─────────────────────┼───────────────────────────────────────────────┤
│  Nova Lite           │  Structures raw SEC filing text extracted by   │
│  (reasoning)        │  Nova Act into key_facts, sentiment, impact     │
├─────────────────────┼───────────────────────────────────────────────┤
│  Nova Multimodal    │  Embeds market event text into 1024-dim         │
│  Embeddings         │  vectors stored in FAISS for historical search. │
├─────────────────────┼───────────────────────────────────────────────┤
│  Nova Act           │  Browser automation — navigates TradingView     │
│                     │  for charts AND opens each SEC EDGAR filing     │
│                     │  document to read its actual content.           │
└─────────────────────┴───────────────────────────────────────────────┘
```

---

## SEC EDGAR — Nova Act Deep Dive

> A screenshot of a filing list is not analysis. SentinelIQ **opens and reads each filing.**

```
Nova Act Session (per ticker, cached 1 hour)
│
├── 1. Navigate to sec.gov/cgi-bin/browse-edgar?CIK={ticker}
│         ↓
│   Extract top 3 filings as JSON
│   [{ form_type, filing_date, description, documents_url }]
│
├── 2. For each filing:
│     │
│     ├── Navigate to documents index page
│     │       ↓
│     ├── Find primary .htm document URL
│     │       ↓
│     ├── Navigate to the actual document
│     │       ↓
│     └── Extract content → { key_facts[], sentiment, impact_summary }
│
└── 3. Nova Lite structures raw extraction into FilingAnalysis schema
          ↓
    Rendered as cards in:
    ├── Alert emails
    └── Market page UI
```

---

## Tech Stack

```
┌─────────────────────────────────────────────────────────────────────┐
│  BACKEND                                                            │
│  FastAPI (Python 3.11, fully async)                                 │
│  PostgreSQL — asyncpg + SQLAlchemy 2.0 async                        │
│  Redis — aioredis (cache + pub/sub)                                 │
│  FinBERT (ProsusAI/finbert) — sentiment classification              │
│  IsolationForest (scikit-learn) — anomaly detection                 │
│  FAISS (faiss-cpu) — vector similarity search                       │
│  LangSmith — full agentic trace observability                       │
├─────────────────────────────────────────────────────────────────────┤
│  FRONTEND                                                           │
│  React 18 + TypeScript + Vite                                       │
│  Tailwind CSS                                                       │
│  TanStack Query (server state)                                      │
│  Zustand (client state)                                             │
│  Recharts (market charts)                                           │
├─────────────────────────────────────────────────────────────────────┤
│  AWS INFRASTRUCTURE                                                 │
│  App Runner — backend container hosting                             │
│  ECR — Docker image registry                                        │
│  Amplify — frontend hosting + CI/CD                                 │
│  Bedrock — Nova Lite, Nova Embeddings                               │
│  Nova Act — browser automation                                      │
├─────────────────────────────────────────────────────────────────────┤
│  EXTERNAL DATA                                                      │
│  NewsAPI — financial headlines                                      │
│  Polygon.io — market data                                           │
│  Twitter/X — social signals                                         │
│  Reddit — r/wallstreetbets, r/stocks                                │
│  SEC EDGAR — regulatory filings                                     │
│  Alpaca Markets — trade execution                                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Application Pages

| Page | What It Does |
|---|---|
| **Dashboard** | Real-time alert feed via WebSocket. Each card shows ticker, sentiment, confidence score, event summary, recommended actions. |
| **Market** | Live quote lookup + news feed + SEC filings analyzed by Nova Act (form type, sentiment, key facts, filing link). |
| **Alerts** | Full alert history with read/unread state. Filter by ticker or date. |
| **Watchlist** | Add/remove tickers. Alerts are only sent for tickers you follow. |
| **Settings** | Alert sensitivity threshold, email preferences, profile management. |
| **Trade Confirm** | Execute trades via Alpaca from alert recommendations. |

---

## API Reference

**Base URL:** `https://xma6vfhzzb.us-east-1.awsapprunner.com/api/v1`

```
Auth
  POST  /auth/register          → Create account
  POST  /auth/login             → Get JWT token

User
  GET   /users/me               → Current user profile
  PATCH /users/me/preferences   → Update alert sensitivity

Watchlist
  GET   /watchlist              → List all tickers
  POST  /watchlist              → Add ticker
  DELETE /watchlist/{ticker}    → Remove ticker

Alerts
  GET   /alerts                 → All alerts for current user
  GET   /alerts/{id}            → Single alert detail
  PATCH /alerts/{id}/read       → Mark as read

Market
  GET   /market/quote/{ticker}  → Live quote (price, change, volume)
  GET   /market/news            → Latest financial news
  GET   /market/filings/{ticker}→ Nova Act EDGAR analysis (3 filings)

WebSocket
  WS    /ws/alerts?token=<jwt>  → Real-time alert stream

Dev (MOCK_MODE only)
  POST  /dev/inject-signal      → Inject test signal
```

---

## Running Locally

### Prerequisites
- Docker, Python 3.11+, Node 18+
- AWS credentials with Bedrock access
- Nova Act API key (`nova.amazon.com/act`)

### Backend

```bash
# Infrastructure
docker-compose up -d

# Dependencies
pip install -r requirements.txt

# Configure (fill in AWS keys, Nova Act key, API keys)
cp .env.example .env

# Seed models + data
python scripts/train_anomaly.py
python scripts/seed_faiss.py
python scripts/seed_db.py

# Start
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev   # → http://localhost:5173
```

### Demo Mode (no API keys needed)

```bash
# In .env
MOCK_MODE=true
```

- Mock signals fire every **30 seconds** automatically
- Nova's agentic decisions are deterministically simulated
- Demo login: `demo@sentineliq.ai` / `demo1234`
- Pre-loaded watchlist: **TSLA · AAPL · NVDA · META · SPY**

### Inject a Test Signal

```bash
# Earnings beat on TSLA
python scripts/simulate_event.py \
  --ticker TSLA --event earnings_beat \
  --email demo@sentineliq.ai --password demo1234

# Force dispatch (bypass Nova — guaranteed alert, great for demos)
python scripts/simulate_event.py \
  --ticker NVDA --event analyst_upgrade --force \
  --email demo@sentineliq.ai --password demo1234
```

Available events: `earnings_beat` · `earnings_miss` · `analyst_upgrade` · `macro_event`

---

## Deploying to AWS

### Backend (ECR → App Runner)

```bash
# 1. Authenticate ECR (token expires every 12h)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  307946674899.dkr.ecr.us-east-1.amazonaws.com

# 2. Build & push (BuildKit enabled — pip layer cached)
DOCKER_BUILDKIT=1 docker build -t sentineliqbackend .
docker tag sentineliqbackend:latest \
  307946674899.dkr.ecr.us-east-1.amazonaws.com/sentineliqbackend:latest
docker push \
  307946674899.dkr.ecr.us-east-1.amazonaws.com/sentineliqbackend:latest

# 3. Update App Runner (new image + env vars)
aws apprunner update-service \
  --service-arn arn:aws:apprunner:us-east-1:307946674899:service/sentineliq/806542f87a7c4d44bb72ae357a9421a4 \
  --source-configuration file://source-config.json \
  --region us-east-1

# 4. Check status
aws apprunner describe-service \
  --service-arn arn:aws:apprunner:us-east-1:307946674899:service/sentineliq/806542f87a7c4d44bb72ae357a9421a4 \
  --region us-east-1 --query "Service.Status"
# → "RUNNING" when live
```

### Frontend (Amplify)

```bash
git push origin main   # Amplify auto-deploys on push
```

---

## Project Structure

```
SentinelIQ/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py          ← Nova Lite agentic tool-calling loop
│   │   ├── credibility_checker.py   ← Source trust scoring
│   │   └── personalization_agent.py ← Watchlist-based user matching
│   ├── ingestion/
│   │   ├── pipeline.py              ← asyncio.Queue coordinator
│   │   └── normalizer.py            ← RawSignal schema
│   ├── ml/
│   │   ├── sentiment/               ← FinBERT classifier
│   │   ├── anomaly/                 ← IsolationForest
│   │   └── embeddings/              ← Nova embeddings + FAISS store
│   ├── services/
│   │   ├── nova_act_edgar.py        ← Nova Act EDGAR deep analysis
│   │   ├── nova_act_trader.py       ← Nova Act Alpaca trade execution
│   │   ├── nova_reasoning.py        ← Nova Lite Bedrock Converse calls
│   │   ├── alert_dispatcher.py      ← DB + Redis + WS + Email
│   │   ├── email_sender.py          ← Rich HTML alert emails
│   │   ├── chart_capture.py         ← TradingView screenshot
│   │   └── websocket_manager.py     ← WS connection manager
│   ├── api/v1/                      ← FastAPI route handlers
│   ├── config.py                    ← All settings via pydantic-settings
│   └── main.py                      ← App entrypoint + lifespan
│
├── frontend/src/
│   ├── pages/                       ← Dashboard, Market, Alerts, Watchlist, Settings
│   └── api/                         ← Typed API client functions
│
├── scripts/
│   ├── simulate_event.py            ← Inject test signals for demo
│   ├── seed_db.py                   ← Demo user + watchlist
│   ├── seed_faiss.py                ← Historical event embeddings
│   └── train_anomaly.py             ← IsolationForest training
│
├── Dockerfile                       ← Backend container (App Runner)
├── docker-compose.yml               ← Local Postgres + Redis
└── source-config.json               ← App Runner deployment config
```

---

## Built With Amazon Nova

> Nova Lite · Nova Multimodal Embeddings · Nova Act

SentinelIQ demonstrates what's possible when you give an AI model tools and autonomy — not a pipeline, but a genuine decision-making agent that separates signal from noise in real-time financial markets.
