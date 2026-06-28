# FinAI Platform — Architecture Documentation

## Overview

FinAI is a production-ready AI-powered financial intelligence platform built
with Python 3.12 / FastAPI, using a clean modular architecture that separates
concerns across layers.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx (TLS, Rate Limiting)              │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│               FastAPI Application (4 Uvicorn Workers)           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────┐  │
│  │ Auth     │  │ Finance  │  │ Market   │  │ AI/ML Routes  │  │
│  │ Routes   │  │ Routes   │  │ Routes   │  │ (Chat/Predict)│  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └───────┬────────┘  │
│       │              │              │                 │           │
│  ┌────▼──────────────▼──────────────▼─────────────────▼───────┐  │
│  │                  Service Layer                               │  │
│  │  AuthService | FinancialService | NotificationService       │  │
│  └────┬──────────────┬──────────────┬──────────────────────────┘  │
│       │              │              │                              │
│  ┌────▼─────┐  ┌─────▼────┐  ┌─────▼─────┐                       │
│  │Repository│  │ML Services│  │Graph Svc  │                       │
│  │  Layer   │  │(FinBERT, │  │(Neo4j     │                       │
│  │          │  │ Predict, │  │ Queries)  │                       │
│  │          │  │ Risk, Rec│  │           │                       │
│  └────┬─────┘  └──────────┘  └─────┬─────┘                       │
└───────┼──────────────────────────── ┼───────────────────────────┘
        │                             │
┌───────▼─────┐  ┌──────────┐  ┌─────▼─────┐  ┌─────────────────┐
│ PostgreSQL  │  │  Redis   │  │  Neo4j    │  │  FAISS/Vector   │
│ (Structured)│  │ (Cache,  │  │  (Graph,  │  │  Store (RAG)    │
│             │  │  Sessions│  │  Relations│  │                 │
└─────────────┘  └──────────┘  └───────────┘  └─────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    Celery Workers (Async Jobs)                   │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │ Market Tasks   │  │    ML Tasks     │  │  Notification    │  │
│  │ (Yahoo/Gecko/  │  │ (FinBERT, Pred, │  │  Tasks          │  │
│  │  NewsAPI/Bin.) │  │  Rec, Health)   │  │                  │  │
│  └────────────────┘  └─────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Module Communication

### Request Flow (Typical API Call)
1. **Nginx** receives HTTPS request, applies rate limiting, proxies to FastAPI
2. **Middleware** extracts JWT, sets request context (request_id, user_id)
3. **Router** dispatches to correct route handler
4. **Route** validates request via Pydantic schema, injects dependencies
5. **Service** executes business logic, calls repositories and ML services
6. **Repository** executes async SQL via SQLAlchemy 2.0
7. **GraphService** optionally syncs to Neo4j for relationship queries
8. **Response** serialized via Pydantic, returned through middleware chain

### Background Job Flow
1. **Celery Beat** fires scheduled task (e.g., `fetch_and_store_news` every hour)
2. **Celery Worker** receives task, creates asyncio event loop
3. **Collector** fetches external data (Yahoo Finance, NewsAPI, CoinGecko)
4. **Repository** persists raw data to PostgreSQL
5. **ML Service** processes data (FinBERT sentiment, technical indicators)
6. **GraphService** syncs relationships and sentiments to Neo4j
7. **NotificationService** checks thresholds and creates user notifications

## Database Design

### PostgreSQL (Structured Data)
- **Users**: identity, auth, financial profile, risk tolerance
- **Wallets**: bank accounts with balance and type
- **Incomes/Expenses**: cash flow tracking with frequency normalization
- **Loans**: debt tracking with amortization metadata
- **SavingsGoals**: goal-based saving with progress tracking
- **Investments/CryptoHoldings**: portfolio positions with P&L
- **MarketSnapshots**: OHLCV time-series data
- **NewsArticles**: with FinBERT sentiment scores
- **TechnicalIndicators**: RSI, MACD, Bollinger, etc.
- **Predictions**: ML model outputs with confidence
- **Recommendations**: personalized actions with explanations
- **Notifications**: user alerts and events

### Neo4j (Graph Intelligence)
The graph captures relationships that are expensive or complex in SQL:

```cypher
(User)-[:HAS_WALLET]->(Wallet)
(User)-[:OWES]->(Loan)
(User)-[:INVESTED_IN {quantity, avg_price}]->(Asset)
(User)-[:HAS_GOAL]->(Goal)
(News)-[:SENTIMENT_TOWARD {score, label}]->(Asset)
(Prediction)-[:PREDICTS]->(Asset)
(Recommendation)-[:RECOMMENDS]->(User)
```

Key graph queries:
- **Context extraction**: Pull full user financial context in one query for RAG
- **Sentiment aggregation**: Aggregate news sentiment per asset across time
- **Portfolio intelligence**: Enrich holdings with sentiment + prediction signals
- **Debt arbitrage**: Find optimal debt payoff order considering total picture

## ML Pipeline

### FinBERT Sentiment Pipeline
```
NewsAPI → Store Articles → FinBERT Batch Inference → 
Sentiment Scores → PostgreSQL Update → Neo4j Sentiment Edges → 
Threshold Check → Notification Dispatch
```

### Market Prediction Pipeline
```
Yahoo Finance OHLCV → Technical Indicator Engine → 
Feature Matrix (22 features) → LightGBM + XGBoost Ensemble → 
Direction + Confidence → PostgreSQL → Neo4j Prediction Node
```

### Recommendation Pipeline
```
User Financial State → Risk Engine (5 components) → 
Priority Filtering (Emergency Fund → Debt → Goals → Invest) →
Market Signals (Prediction + Sentiment) → 
Explainable Recommendations → PostgreSQL → Notification
```

### RAG Chatbot Pipeline
```
User Message → Neo4j Context Fetch → Document Chunking → 
FAISS Semantic Search → Context Assembly → Prompt Building →
Open-Source LLM (Mistral/Llama) → Response → 
Redis Memory Update
```

## Scalability Strategy

### Horizontal Scaling
- FastAPI stateless workers → scale API pods independently
- Celery workers → scale by queue (ML tasks separate from market tasks)
- PostgreSQL read replicas for analytics queries
- Redis Cluster for distributed caching

### Performance Optimisations
- Async I/O throughout (asyncpg, aiohttp, aioredis)
- Connection pooling (PG: pool_size=20, Neo4j: max_pool=50)
- Redis caching for hot paths (market prices: 60s TTL, user context: 5min)
- Prometheus metrics for latency/throughput observability
- GZip middleware for large responses
- Nginx upstream keepalive connections

### Security
- JWT access tokens (30min) + Redis-backed refresh tokens (7 days)
- bcrypt password hashing (cost=12)
- Per-user rate limiting (60 req/min)
- CORS, CSRF via middleware
- SQL injection: prevented by SQLAlchemy parameterization
- Cypher injection: prevented by parameterized queries
- Audit logging: all auth events logged with structlog
- Non-root Docker user
- Secrets via environment variables (never hardcoded)

## Deployment

### Production Stack
```
Load Balancer
  └── Nginx (TLS termination, rate limiting)
        └── FastAPI (4+ workers, uvloop)
              ├── PostgreSQL 16 (primary + 1 read replica)
              ├── Neo4j 5.x Community / Enterprise
              ├── Redis 7.x (sentinel for HA)
              └── Celery (2+ workers + 1 beat)

Monitoring: Prometheus → Grafana
Logs: structlog JSON → ELK / Datadog
CI/CD: GitHub Actions → SSH deploy
```

### Environment Progression
`development` → `staging` → `production`

All configuration via `.env` — never hardcode credentials.
