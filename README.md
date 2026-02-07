# Axiomeer - AI Agent API Marketplace

![Axiomeer Banner](Test%20Images/Banner.png)

> An intelligent marketplace where AI agents autonomously discover, evaluate, and execute APIs to fulfill their tasks. Powered by semantic search, LLM-driven capability extraction, and weighted multi-factor ranking.

[![Version](https://img.shields.io/badge/version-6.0--mvp-blue.svg)](https://github.com/ujjwalredd/axiomeer)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![APIs](https://img.shields.io/badge/apis-91%20active-success.svg)](#api-catalog)
[![Pass Rate](https://img.shields.io/badge/pass%20rate-80.2%25-green.svg)](#quality-metrics)

![Demo](Test%20Images/Axiomeer.gif)

---

## Table of Contents

- [What is Axiomeer?](#what-is-axiomeer)
- [How AI Agents Connect](#how-ai-agents-connect-to-the-marketplace)
- [Core Architecture](#core-architecture)
- [Key Features](#key-features)
- [API Catalog - 91 APIs](#api-catalog)
- [Quick Start](#quick-start)
- [Authentication & Security](#authentication--security)
- [Usage Guide](#usage-guide)
- [Technical Stack](#technical-stack)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## What is Axiomeer?

**Axiomeer** is a production-ready AI marketplace platform that acts as an **intelligent intermediary between AI agents and external APIs**. Instead of hardcoding API integrations, AI agents can use natural language to describe what they need, and Axiomeer automatically:

1. **Discovers** relevant APIs from a catalog of 91+ services
2. **Evaluates** them using weighted scoring (capability match, relevance, trust, performance)
3. **Executes** the best-matched API with validated inputs/outputs
4. **Tracks** usage, costs, and provenance for audit trails

### The Problem Axiomeer Solves

**Traditional Approach:**
```python
# AI agent needs to hardcode every API integration
if task == "weather":
    response = requests.get("https://api.weather.com/...")
elif task == "stock price":
    response = requests.get("https://api.stocks.com/...")
# ... hundreds of if-else statements
```

**Axiomeer Approach:**
```python
# AI agent asks the marketplace
result = axiomeer.shop("Get current weather in Paris")
# Marketplace automatically finds and executes best weather API
```

### Key Benefits

- **Autonomous Discovery:** AI agents find APIs without human intervention
- **Intelligent Routing:** Multi-factor scoring ensures best API selection
- **Automatic Validation:** Outputs are validated for citations, timestamps, quality
- **Built-in Authentication:** Enterprise-grade JWT + API key management
- **Rate Limiting:** Tier-based quotas prevent abuse
- **Provenance Tracking:** Full audit trail of all executions
- **Semantic Search:** Find APIs using natural language, not exact keywords

---

## How AI Agents Connect to the Marketplace

### Workflow Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Step 1: AI Agent Needs Information                         │
│  "I need to know the weather in Paris"                      │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 2: Agent Connects to Axiomeer Marketplace             │
│  POST /shop with task description                           │
│  {                                                          │
│    "task": "Get current weather in Paris",                  │
│    "required_capabilities": ["weather", "realtime"]         │
│  }                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 3: Marketplace Intelligence Layer                     │
│                                                             │
│  a) LLM Capability Extraction (Ollama)                      │
│     Input: "Get current weather in Paris"                   │
│     Output: ["weather", "realtime", "geographic"]           │
│                                                             │
│  b) Semantic Search (FAISS + Embeddings)                    │
│     - Converts task to 384-dim vector                       │
│     - Searches 91 API embeddings                            │
│     - Returns top 20 relevant matches                       │
│     - Fallback: TF-IDF if semantic unavailable              │
│                                                             │
│  c) Weighted Ranking Algorithm                              │
│     score = (0.70 × capability_match) +                     │
│             (0.25 × relevance_score) +                      │
│             (0.15 × trust_score) -                          │
│             (0.20 × latency_penalty) -                      │
│             (0.10 × cost_penalty)                           │
│                                                             │
│     Filters:                                                │
│     - 100% capability coverage required                     │
│     - Minimum relevance: 0.08                               │
│     - Minimum total score: 0.55                             │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 4: Marketplace Returns Ranked Recommendations         │
│  {                                                          │
│    "recommendations": [                                     │
│      {                                                      │
│        "app_id": "realtime_weather_agent",                  │
│        "score": 0.89,                                       │
│        "capability_match": 1.0,                             │
│        "relevance_score": 0.92,                             │
│        "trust_score": 0.75,                                 │
│        "latency_ms": 800                                    │
│      },                                                     │
│      {...}                                                  │
│    ],                                                       │
│    "explanation": {                                         │
│      "summary": "Recommended realtime_weather_agent...",    │
│      "rationale": "Best match for real-time weather..."     │
│    }                                                        │
│  }                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 5: Agent Selects & Executes API                       │
│  POST /execute                                              │
│  {                                                          │
│    "app_id": "realtime_weather_agent",                      │
│    "task": "Weather in Paris",                              │
│    "inputs": {"lat": 48.8566, "lon": 2.3522},               │
│    "require_citations": true                                │
│  }                                                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 6: Marketplace Executes Provider                      │
│  - Validates inputs (Pydantic schemas)                      │
│  - Makes HTTP call to provider endpoint                     │
│  - Validates output (citations, timestamps)                 │
│  - Records execution in database (provenance)               │
│  - Tracks usage for rate limiting/billing                   │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│  Step 7: Agent Receives Validated Result                    │
│  {                                                          │
│    "ok": true,                                              │
│    "run_id": 42,                                            │
│    "output": {                                              │
│      "answer": "Paris: 12°C, Partly cloudy, Wind: 15km/h",  │
│      "citations": ["https://open-meteo.com"],               │
│      "retrieved_at": "2026-02-07T14:30:00Z",                │
│      "quality": "verified"                                  │
│    },                                                       │
│    "latency_ms": 850,                                       │
│    "cost_usd": 0.0                                          │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
```

### Integration Methods for AI Agents

#### Method 1: Direct HTTP API

Any AI agent can connect via standard HTTP requests:

```python
import requests

API_KEY = "your_api_key"
headers = {"X-API-Key": API_KEY}

# 1. Discover APIs
response = requests.post(
    "http://localhost:8000/shop",
    headers=headers,
    json={
        "task": "Get Bitcoin price in USD",
        "required_capabilities": ["finance", "cryptocurrency"]
    }
)

recommendations = response.json()["recommendations"]
best_api = recommendations[0]["app_id"]

# 2. Execute best API
result = requests.post(
    "http://localhost:8000/execute",
    headers=headers,
    json={
        "app_id": best_api,
        "task": "Get Bitcoin price",
        "inputs": {"currency_pair": "BTC-USD"},
        "require_citations": True
    }
)

print(result.json()["output"]["answer"])
```

#### Method 2: Python SDK (Coming Soon)

```python
from axiomeer import Marketplace

marketplace = Marketplace(api_key="your_key")

# One-line execution
result = marketplace.execute(
    task="Get weather in Tokyo",
    auto_discover=True
)

print(result.answer)  # "Tokyo: 5°C, Clear sky..."
```

#### Method 3: LangChain Integration (Coming Soon)

```python
from langchain.agents import initialize_agent
from langchain_axiomeer import AxiomeerToolkit

toolkit = AxiomeerToolkit(api_key="your_key")
agent = initialize_agent(
    toolkit.get_tools(),
    llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION
)

agent.run("What's the weather in Paris and the Bitcoin price?")
# Agent automatically uses Axiomeer to find and execute APIs
```

---

## Core Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER                                │
│  AI Agents, Web Apps, Mobile Apps, CLI Tools                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ HTTPS + JWT/API Key
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 AUTHENTICATION & RATE LIMITING                  │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐   │
│  │  JWT Tokens    │  │   API Keys      │  │  Rate Limiter   │   │
│  │  (python-jose) │  │  (SHA-256 hash) │  │  (Tier-based)   │   │
│  └────────────────┘  └─────────────────┘  └─────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FASTAPI APPLICATION                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              CORE ENDPOINTS                              │   │
│  │  /shop  → Discover & rank APIs                           │   │
│  │  /execute → Execute specific API                         │   │
│  │  /apps → List all available APIs                         │   │
│  │  /runs → View execution history                          │   │
│  └──────────────────────────────────────────────────────────┘   │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   INTELLIGENCE LAYER                            │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  LLM Capability Extractor (Ollama phi3.5:3.8b)             │ │
│  │  - Analyzes natural language task                          │ │
│  │  - Extracts required capabilities                          │ │
│  │  - Infers constraints (freshness, cost, latency)           │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Semantic Search Engine (FAISS + sentence-transformers)    │ │
│  │  - 384-dimensional embeddings                              │ │
│  │  - all-MiniLM-L6-v2 model                                  │ │
│  │  - Sub-50ms similarity search                              │ │
│  │  - TF-IDF fallback                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Weighted Ranking Algorithm                                │ │
│  │  - Capability matching (70% weight)                        │ │
│  │  - Semantic relevance (25% weight)                         │ │
│  │  - Trust score (15% weight)                                │ │
│  │  - Latency penalty (20% weight)                            │ │
│  │  - Cost consideration (10% weight)                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Sales Agent (LLM Explanations)                            │ │
│  │  - Explains why APIs were recommended                      │ │
│  │  - Describes tradeoffs                                     │ │
│  │  - Provides rationale for rankings                         │ │
│  └────────────────────────────────────────────────────────────┘ │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    PROVIDER LAYER                               │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  91 Provider Endpoints (apps/api/providers.py)           │   │
│  │  - Financial: Coinbase, CoinGecko, Exchange Rates...     │   │
│  │  - Weather: Open-Meteo, Nominatim...                     │   │
│  │  - Knowledge: Wikipedia, ArXiv, PubMed...                │   │
│  │  - Entertainment: Pokemon, Rick&Morty, Cat Facts...      │   │
│  │  - [... 8 more categories]                               │   │
│  └──────────────────────────────────────────────────────────┘   │
│  Each provider:                                                 │
│  - Makes HTTP call to external API                              │
│  - Transforms response to standard format                       │
│  - Adds citations and metadata                                  │
│  - Implements caching where appropriate                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   VALIDATION & STORAGE                          │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Output Validator                                          │ │
│  │  - Verifies citation URLs                                  │ │
│  │  - Validates timestamps                                    │ │
│  │  - Checks quality markers                                  │ │
│  │  - Assigns quality scores                                  │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  PostgreSQL Database                                       │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐    │ │
│  │  │ Users        │  │ API Keys     │  │  Rate Limits   │    │ │
│  │  │ - Auth data  │  │ - Hashed     │  │  - Per-user    │    │ │
│  │  └──────────────┘  └──────────────┘  └────────────────┘    │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐    │ │
│  │  │ Runs         │  │ Messages     │  │  App Listings  │    │ │
│  │  │ - Provenance │  │ - Conv logs  │  │  - Manifests   │    │ │
│  │  └──────────────┘  └──────────────┘  └────────────────┘    │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow Example

**Query:** "What's the weather in Paris with citations?"

1. **Authentication:** API key validated → user tier checked
2. **Rate Limiting:** Check if user within hourly quota
3. **LLM Extraction:** Ollama extracts: `["weather", "realtime", "citations", "geographic"]`
4. **Semantic Search:** FAISS finds top 20 matches from 91 APIs
5. **Ranking:** Weighted scoring applied:
   - `realtime_weather_agent`: score 0.89 (best match)
   - `nominatim_geocoding`: score 0.42 (lower relevance)
6. **Sales Agent:** LLM explains: "realtime_weather_agent provides current weather with citations"
7. **Execution:** Agent chooses top recommendation, marketplace calls provider
8. **Provider:** Hits Open-Meteo API, transforms response
9. **Validation:** Checks citations present, validates timestamp
10. **Storage:** Logs to database (run_id=42)
11. **Response:** Returns to agent with validated output

---

## Key Features

### 1. Semantic Search with FAISS

**How it works:**
- Each of 91 APIs has a pre-computed 384-dimensional embedding
- Query is embedded using same model (`all-MiniLM-L6-v2`)
- FAISS performs cosine similarity search in <50ms
- Returns top 20 most semantically similar APIs
- Falls back to TF-IDF if embeddings unavailable

**Example:**
```
Query: "stock market data"
Embedding: [0.12, -0.45, 0.78, ... 384 dims]

Similarity scores:
- coinbase_prices: 0.89 
- coingecko_crypto: 0.85 
- nasa_apod: 0.12 (filtered out)
```

### 2. Multi-Factor Weighted Ranking

**Scoring Algorithm:**

```python
def calculate_score(api, query):
    # Capability match (70% weight) - MUST be 100%
    capability_score = 1.0 if all_capabilities_present else 0.0
    
    # Semantic relevance (25% weight)
    relevance_score = cosine_similarity(query_embedding, api_embedding)
    
    # Trust score (15% weight)
    trust_score = (successful_runs / total_runs) * 0.5 + 
                  (citations_provided ? 0.3 : 0) +
                  (verified_provider ? 0.2 : 0)
    
    # Latency penalty (20% weight)
    latency_penalty = 1.0 - (min(latency_ms, 5000) / 5000)
    
    # Cost penalty (10% weight)
    cost_penalty = 1.0 - (min(cost_usd, 1.0) / 1.0)
    
    # Weighted sum (normalized)
    score = (0.70 * capability_score +
             0.25 * relevance_score +
             0.15 * trust_score +
             0.20 * latency_penalty +
             0.10 * cost_penalty) / sum_of_weights
    
    return score
```

**Filters Applied:**
- Capability coverage must be 100%
- Relevance score minimum: 0.08
- Total score minimum: 0.55

### 3. LLM-Powered Capability Extraction

**Without LLM:**
```python
# Agent must manually specify capabilities
result = marketplace.shop(
    task="Get weather",
    required_capabilities=["weather", "realtime", "geographic", "citations"]
)
```

**With LLM (Automatic):**
```python
# Agent just describes what they need
result = marketplace.shop(
    task="Show me current weather in Paris with sources",
    auto_caps=True  # LLM extracts: ["weather", "realtime", "geographic", "citations"]
)
```

**LLM Prompt Template:**
```
Given this task: "{task}"

Extract required capabilities from this list:
- weather, finance, cryptocurrency, knowledge, search, realtime, citations, 
  geographic, government, media, entertainment, translation, ai, etc.

Return ONLY a JSON array: ["cap1", "cap2", ...]
```

### 4. Enterprise Authentication

**Three-Layer Security:**

1. **User Accounts** (PostgreSQL)
   - Email/password authentication
   - bcrypt password hashing (cost factor: 12)
   - Email verification (optional)
   - User tiers (free, starter, pro, enterprise)

2. **JWT Tokens** (Short-lived Sessions)
   - HMAC-SHA256 signing
   - 60-minute expiration (configurable)
   - Stateless validation
   - Used for /auth endpoints

3. **API Keys** (Long-lived Access)
   - SHA-256 hashed storage
   - Prefix system for identification (`axm_xxxxx...`)
   - Per-key rate limiting
   - Used for /shop and /execute

### 5. Tier-Based Rate Limiting

**How it works:**
- Each request checks user's tier
- Tracks requests per rolling 1-hour window
- Returns 429 with `X-RateLimit-*` headers when exceeded
- Resets automatically after window expires

**Tier Limits:**

| Tier | Requests/Hour | Monthly Cost | Limit Reset |
|------|---------------|--------------|-------------|
| Free | 100 | $0 | Rolling 1-hour window |
| Starter | 1,000 | TBD | Rolling 1-hour window |
| Pro | 10,000 | TBD | Rolling 1-hour window |
| Enterprise | Custom | Custom | Configurable |

**Rate Limit Headers:**
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 3456  (seconds until reset)
```

### 6. Provenance & Audit Trail

Every execution is logged with:
- **Run ID:** Unique identifier
- **User ID:** Who executed
- **App ID:** Which API was used
- **Task:** What was requested
- **Inputs:** What parameters were sent
- **Output:** What was returned
- **Citations:** Where data came from
- **Timestamp:** When it occurred
- **Latency:** How long it took
- **Cost:** Resource usage

**Query execution history:**
```bash
curl -H "X-API-Key: $KEY" http://localhost:8000/runs?limit=10
```

---

## API Catalog

### 91 Active APIs Across 11 Categories

| Category | Count | Examples | Pass Rate |
|----------|-------|----------|-----------|
| **Financial** | 4 | Coinbase, CoinGecko, Blockchain.info, Exchange Rates | 100% |
| **Geographic** | 4 | Weather, Nominatim, Geonames, IP Geolocation | 75% |
| **Knowledge** | 12 | Wikipedia, ArXiv, PubMed, Wikidata, DBpedia | 83% |
| **Government** | 8 | World Bank, FRED, COVID Stats, UK Police | 50% |
| **Media** | 6 | OMDB, TMDB, MusicBrainz, Genius, Unsplash | 100% |
| **NASA** | 3 | APOD, Mars Rover, Asteroids | 67% |
| **Utilities** | 17 | Dictionary, QR, UUID, Base64, HTTPBin | 83% |
| **Entertainment** | 5 | Cat Facts, Dog Images, Pokemon, Rick & Morty | 80% |
| **Food** | 3 | TheMealDB, CocktailDB, Fruityvice | 100% |
| **Fun** | 8 | Chuck Norris, Coin Flip, Dice Roll, Yes/No | 88% |
| **Science** | 5 | Newton Math, Periodic Table, Sunrise/Sunset | 80% |
| **Language** | 6 | Definitions, Synonyms, Language Detection, Datamuse | 83% |
| **AI Models** | 4 | Ollama (Llama3, Mistral, CodeLlama, Deepseek) | 100%|

**Overall Pass Rate:** 73/91 working (80.2%)

For complete API documentation, see [Product Guide PDF](docs/axiomeer_product_guide.pdf)

---

## Quick Start

### Docker Deployment (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/ujjwalredd/axiomeer.git
cd axiomeer

# 2. Generate secrets
export JWT_SECRET_KEY=$(openssl rand -base64 32)
export DB_PASSWORD=$(openssl rand -base64 16)

# 3. Create .env file
cat > .env << EOF
DATABASE_URL=postgresql://axiomeer:${DB_PASSWORD}@db:5432/axiomeer
DB_PASSWORD=${DB_PASSWORD}
AUTH_ENABLED=true
JWT_SECRET_KEY=${JWT_SECRET_KEY}
RATE_LIMIT_ENABLED=true
OLLAMA_URL=http://host.docker.internal:11434/api/generate
SEMANTIC_SEARCH_ENABLED=true
EOF

# 4. Start services
docker-compose up -d

# 5. View logs
docker-compose logs -f api

# 6. Test deployment
curl http://localhost:8000/health
# Output: {"status":"ok"}

curl http://localhost:8000/apps | jq 'length'
# Output: 91
```

### Local Development

```bash
# 1. Prerequisites
# - Python 3.10+
# - PostgreSQL 15
# - Ollama (for LLM features)

# 2. Setup Python environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install -e ".[dev]"

# 3. Setup database
createdb axiomeer
alembic upgrade head

# 4. Install and configure Ollama
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3.5:3.8b

# 5. Configure environment
cp .env.example .env
nano .env  # Set JWT_SECRET_KEY, DATABASE_URL

# 6. Start server
uvicorn apps.api.main:app --reload --port 8000

# 7. Open browser
# http://localhost:8000/docs (Swagger UI)
```

---

## Authentication & Security

### Creating an Account

```bash
# Signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "agent@example.com",
    "username": "my_ai_agent",
    "password": "SecurePassword123!"
  }'

# Response
{
  "id": 1,
  "email": "agent@example.com",
  "username": "my_ai_agent",
  "tier": "free",
  "is_active": true,
  "created_at": "2026-02-07T14:00:00Z"
}
```

### Getting Access Tokens

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "agent@example.com",
    "password": "SecurePassword123!"
  }'

# Response
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

### Creating API Keys

```bash
# Save your JWT token
TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Create API key
curl -X POST http://localhost:8000/auth/api-keys \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Production Agent Key"}'

# Response
{
  "id": 1,
  "name": "Production Agent Key",
  "key_prefix": "axm_9HDg-hp2",
  "key": "axm_9HDg-hp2gJdwMVN2gjQl6i8LAkCt9S7S7DxQgROYciU",
  "is_active": true,
  "created_at": "2026-02-07T14:05:00Z"
}
```

**IMPORTANT:** Save the `key` value immediately - it's shown only once!

### Using API Keys

```bash
# Save your API key
API_KEY="axm_9HDg-hp2gJdwMVN2gjQl6i8LAkCt9S7S7DxQgROYciU"

# Use in requests
curl -H "X-API-Key: $API_KEY" \
  http://localhost:8000/auth/me

# Or with JSON requests
curl -X POST http://localhost:8000/shop \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"task": "Get weather in Paris", "required_capabilities": ["weather"]}'
```

### Managing API Keys

```bash
# List all your API keys
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/auth/api-keys

# Revoke an API key
curl -X DELETE \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/auth/api-keys/1
```

### Security Features

1. **Password Security**
   - bcrypt hashing with automatic salting
   - Cost factor: 12 (2^12 iterations)
   - Rainbow table resistant

2. **Token Security**
   - JWT with HMAC-SHA256 signing
   - Short expiration (60 minutes)
   - Stateless validation (no DB lookup)

3. **API Key Security**
   - SHA-256 hashed storage
   - Prefix system for easy identification
   - Per-key rate limiting
   - Revocable without affecting other keys

4. **Input Validation**
   - Pydantic schemas on all endpoints
   - Type checking and constraints
   - SQL injection prevention (ORM)

5. **Rate Limiting**
   - Per-user enforcement
   - Rolling window algorithm
   - 429 responses with retry info

---

## Usage Guide

### Getting Started: Direct API Execution

The simplest way to get answers is to **directly execute an API** using `/execute`:

### Scenario 1: Get a Cat Fact 

```bash
curl -s -X POST http://localhost:8000/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "cat_facts",
    "task": "Give me a cat fact",
    "inputs": {},
    "require_citations": true
  }' | jq '{answer: .output.answer, citations: .output.citations}'
```

**Response:**
```json
{
  "answer": "Cat Fact: The tiniest cat on record is Mr. Pebbles, a 2-year-old cat that weighed 3 lbs (1.3 k) and was 6.1 inches (15.5 cm) high.",
  "citations": [
    "https://catfact.ninja"
  ]
}
```

### Scenario 2: Get a Chuck Norris Joke 

```bash
curl -s -X POST http://localhost:8000/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "chuck_norris_jokes",
    "task": "Tell me a joke",
    "inputs": {},
    "require_citations": true
  }' | jq '{answer: .output.answer}'
```

**Response:**
```json
{
  "answer": "Chuck Norris Joke: Every morning, Chuck Norris has a bowl of nails for breakfast."
}
```

### Scenario 3: Flip a Coin

```bash
curl -s -X POST http://localhost:8000/execute \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "coinflip",
    "task": "Flip a coin",
    "inputs": {},
    "require_citations": true
  }' | jq '{answer: .output.answer}'
```

**Response:**
```json
{
  "answer": "Coin Flip Result: Heads"
}
```

### Scenario 2: Complex Multi-Capability Query

**Goal:** Find academic papers with citations

```bash
curl -X POST http://localhost:8000/shop \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Find recent AI research papers with citations",
    "required_capabilities": ["knowledge", "search", "citations", "academic"],
    "constraints": {
      "freshness": "recent",
      "citations_required": true,
      "max_latency_ms": 3000
    }
  }'

# Marketplace finds arxiv_papers, semantic_scholar, etc.
```

### Scenario 3: Automatic Capability Extraction

**Using LLM (Ollama) to extract capabilities:**

```bash
# Instead of manually specifying capabilities, let LLM extract them
curl -X POST http://localhost:8000/shop \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "I need current COVID-19 statistics for the United States with reliable sources",
    "auto_extract_capabilities": true
  }'

# LLM extracts: ["health", "government", "realtime", "citations"]
# Returns: covid_stats API
```

### Scenario 4: Cost-Optimized Search

**Find cheapest option:**

```bash
curl -X POST http://localhost:8000/shop \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Get word definitions and synonyms",
    "required_capabilities": ["language", "definitions"],
    "constraints": {
      "max_cost_usd": 0.0
    }
  }'

# Returns only free language APIs
```

### Scenario 5: View Execution History

```bash
# List recent executions
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/runs?limit=10"

# Get specific execution details
curl -H "X-API-Key: $API_KEY" \
  "http://localhost:8000/runs/42"

# Response includes full provenance
{
  "run_id": 42,
  "user_id": 1,
  "app_id": "coinbase_prices",
  "task": "Get Bitcoin price",
  "inputs": {"currency_pair": "BTC-USD"},
  "output": {...},
  "created_at": "2026-02-07T14:30:00Z",
  "latency_ms": 450,
  "cost_usd": 0.0
}
```

---

## Technical Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API Framework** | FastAPI 0.128+ | High-performance async REST API |
| **Web Server** | Uvicorn | ASGI server for FastAPI |
| **Database** | PostgreSQL 15 | Production data storage |
| **ORM** | SQLAlchemy 2.0 | Database abstraction layer |
| **Migrations** | Alembic 1.18+ | Schema version control |
| **Authentication** | JWT (python-jose) | Stateless token authentication |
| **Password Hashing** | bcrypt | Secure password storage |
| **LLM** | Ollama (phi3.5:3.8b) | Local LLM for capability extraction |
| **Embeddings** | sentence-transformers | Text → vector conversion |
| **Vector Store** | FAISS | Fast similarity search |
| **Relevance** | scikit-learn | TF-IDF scoring |
| **Validation** | Pydantic v2 | Request/response validation |
| **CLI** | Typer + Rich | Command-line interface |
| **Testing** | pytest | Unit and integration tests |
| **Containerization** | Docker + docker-compose | Deployment orchestration |
| **Python** | 3.10+ | Runtime environment |

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
#============================================
# DATABASE
#============================================
DATABASE_URL=postgresql://axiomeer:password@localhost:5432/axiomeer
# For SQLite (dev only): DATABASE_URL=sqlite:///./marketplace.db

#============================================
# AUTHENTICATION (Required in production)
#============================================
AUTH_ENABLED=true
JWT_SECRET_KEY=<generate-with-openssl-rand-base64-32>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
API_KEY_HEADER=X-API-Key

#============================================
# RATE LIMITING
#============================================
RATE_LIMIT_ENABLED=true
RATE_LIMIT_FREE_TIER_PER_HOUR=100
RATE_LIMIT_STARTER_TIER_PER_HOUR=1000
RATE_LIMIT_PRO_TIER_PER_HOUR=10000
RATE_LIMIT_ENTERPRISE_TIER_PER_HOUR=100000

#============================================
# LLM CONFIGURATION
#============================================
OLLAMA_URL=http://localhost:11434/api/generate
ROUTER_MODEL=phi3.5:3.8b
SALES_AGENT_MODEL=phi3.5:3.8b

#============================================
# SEMANTIC SEARCH
#============================================
SEMANTIC_SEARCH_ENABLED=true
SEMANTIC_SEARCH_TOP_K=20
SEMANTIC_SEARCH_MODEL=all-MiniLM-L6-v2

#============================================
# ROUTER WEIGHTS (Normalized at runtime)
#============================================
W_CAP=0.70      # Capability match weight
W_REL=0.25      # Semantic relevance weight
W_TRUST=0.15    # Trust score weight
W_LAT=0.20      # Latency penalty weight
W_COST=0.10     # Cost consideration weight

#============================================
# THRESHOLDS
#============================================
MIN_CAP_COVERAGE=1.0      # 100% capability coverage required
MIN_RELEVANCE_SCORE=0.08  # Minimum semantic relevance
MIN_TOTAL_SCORE=0.55      # Minimum weighted score

#============================================
# CACHING (seconds)
#============================================
SHOP_CACHE_TTL_SECONDS=30
PROVIDER_CACHE_TTL_WEATHER=30
PROVIDER_CACHE_TTL_FX=60
PROVIDER_CACHE_TTL_WIKI=3600
```

### Generating Secrets

```bash
# JWT Secret (32 bytes)
openssl rand -base64 32

# Or using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Database Password
openssl rand -base64 16
```

---

## API Reference

**Base URL:** `http://localhost:8000`

### Core Endpoints

| Method | Endpoint | Description | Auth | Rate Limited |
|--------|----------|-------------|------|--------------|
| GET | `/health` | Health check | No | No |
| GET | `/apps` | List all APIs | No | No |
| GET | `/apps/{app_id}` | Get API details | No | No |
| POST | `/shop` | Discover & rank APIs | Yes | Yes |
| POST | `/execute` | Execute specific API | Yes | Yes |
| GET | `/runs` | List execution history | Yes | No |
| GET | `/runs/{run_id}` | Get execution details | Yes | No |
| GET | `/trust` | Get trust scores | No | No |

### Authentication Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| POST | `/auth/signup` | Create account | No |
| POST | `/auth/login` | Get JWT token | No |
| GET | `/auth/me` | Get current user | Yes |
| POST | `/auth/api-keys` | Create API key | Yes (JWT) |
| GET | `/auth/api-keys` | List API keys | Yes (JWT) |
| DELETE | `/auth/api-keys/{id}` | Revoke API key | Yes (JWT) |

### Request/Response Examples

See [Usage Guide](#usage-guide) section above for detailed examples.

---

## Testing

### Running Tests

```bash
# All tests
pytest -v

# Specific test suites
pytest tests/test_auth.py -v              # Authentication (20 tests)
pytest tests/test_rate_limit.py -v       # Rate limiting (9 tests)
pytest tests/test_router.py -v           # Routing logic (15 tests)
pytest tests/test_api.py -v              # API endpoints (48 tests)

# With coverage report
pytest --cov=src/marketplace --cov-report=html
open htmlcov/index.html

# Exclude integration tests
pytest -m "not integration" -v

# Run benchmark tests (requires running server)
pytest tests/test_benchmarks.py -v
```

### Test Coverage

- **98 total tests**
- **100% backward compatibility** (all existing tests pass)
- **Test Categories:**
  - Authentication: 20 tests
  - Rate limiting: 9 tests  
  - Routing & ranking: 15 tests
  - API endpoints: 48 tests
  - Validation: 6 tests

---

## Troubleshooting

### Docker Issues

```bash
# Check container status
docker ps

# View logs
docker-compose logs -f api
docker-compose logs -f db

# Restart services
docker-compose restart

# Full rebuild
docker-compose down -v
docker-compose up -d --build

# Check API is responding
curl http://localhost:8000/health
```

### Authentication Issues

```bash
# Verify auth is enabled
curl http://localhost:8000/health

# Test signup
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","username":"test","password":"Test123456"}'

# Check JWT secret is set
echo $JWT_SECRET_KEY

# In Docker
docker exec axiomeer_api env | grep JWT_SECRET_KEY
```

### Rate Limiting Issues

```bash
# Check your current rate limit status
curl -H "X-API-Key: $API_KEY" http://localhost:8000/auth/me

# Response includes:
# "tier": "free",
# "rate_limit_per_hour": 100

# Temporarily disable for testing
export RATE_LIMIT_ENABLED=false
docker-compose restart api
```

### Database Issues

```bash
# Run migrations
alembic upgrade head

# Check migration status
alembic current

# Access database
docker exec -it axiomeer_db psql -U axiomeer -d axiomeer

# In psql:
\dt                    # List tables
SELECT COUNT(*) FROM app_listings;
SELECT * FROM users;
\q                     # Quit

# Reset database (deletes all data)
docker-compose down -v
docker-compose up -d
```

### Semantic Search Issues

```bash
# Check if FAISS index is loaded
curl http://localhost:8000/semantic-search/stats

# Response:
{
  "enabled": true,
  "model": "all-MiniLM-L6-v2",
  "index_size": 91,
  "embedding_dim": 384
}

# Rebuild FAISS index
docker exec axiomeer_api python -c "
from marketplace.core.semantic_search import SemanticSearch
search = SemanticSearch()
search.rebuild_index()
"
```

### Ollama Issues

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# Pull required model
ollama pull phi3.5:3.8b

# Test Ollama connection
curl http://localhost:11434/api/generate \
  -d '{"model":"phi3.5:3.8b","prompt":"Say hello","stream":false}'
```

---

## Project Structure

```
axiomeer/
├── apps/
│   └── api/
│       ├── main.py                 # FastAPI application entry point
│       ├── auth_routes.py          # Authentication endpoints
│       └── providers.py            # 91 provider endpoint implementations
│
├── src/marketplace/
│   ├── auth/                       # Authentication module
│   │   ├── dependencies.py         # FastAPI auth dependencies
│   │   ├── security.py             # JWT, bcrypt, password hashing
│   │   ├── models.py               # Pydantic auth request/response models
│   │   └── rate_limiter.py         # Rate limiting implementation
│   │
│   ├── storage/                    # Database layer
│   │   ├── db.py                   # SQLAlchemy setup
│   │   ├── models.py               # App listings ORM model
│   │   ├── runs.py                 # Execution receipts ORM model
│   │   ├── messages.py             # Conversation logs ORM model
│   │   └── users.py                # User, APIKey, RateLimit ORM models
│   │
│   ├── core/                       # Intelligence layer
│   │   ├── router.py               # Weighted ranking algorithm
│   │   ├── semantic_search.py      # FAISS + embeddings
│   │   ├── cap_extractor.py        # LLM capability extraction
│   │   ├── validate.py             # Output validation
│   │   └── models.py               # Core Pydantic schemas
│   │
│   ├── llm/                        # LLM integration
│   │   ├── ollama_client.py        # Ollama HTTP client
│   │   └── sales_agent.py          # Recommendation explanations
│   │
│   ├── cli.py                      # Typer CLI commands
│   └── settings.py                 # Environment configuration
│
├── tests/
│   ├── test_auth.py                # 20 authentication tests
│   ├── test_rate_limit.py          # 9 rate limiting tests
│   ├── test_router.py              # 15 routing/ranking tests
│   ├── test_api.py                 # 48 API endpoint tests
│   ├── test_benchmarks.py          # Performance benchmarks
│   └── conftest.py                 # Pytest fixtures
│
├── alembic/                        # Database migrations
│   ├── env.py                      # Alembic environment
│   └── versions/                   # Migration scripts
│       └── xxxx_create_tables.py
│
├── manifests/categories/           # 91 API manifest files
│   ├── financial/
│   │   ├── coinbase_prices.json
│   │   └── ...
│   ├── knowledge/
│   ├── entertainment/
│   └── ...
│
├── docs/
│   ├── axiomeer_product_guide.pdf  # Complete API catalog
│   └── architecture.md             # Architecture docs
│
├── Dockerfile                      # Docker image definition
├── docker-compose.yml              # Multi-container orchestration
├── alembic.ini                     # Alembic configuration
├── pyproject.toml                  # Python dependencies & metadata
├── .env.example                    # Environment template
├── .dockerignore                   # Docker ignore rules
└── README.md                       # This file
```

---

## Contributing

```bash
# 1. Fork repository on GitHub

# 2. Clone your fork
git clone https://github.com/ujjwalredd/axiomeer.git
cd axiomeer

# 3. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 4. Install in development mode
pip install -e ".[dev]"

# 5. Setup database
alembic upgrade head

# 6. Run tests
pytest -v

# 7. Create feature branch
git checkout -b feature/your-feature-name

# 8. Make changes and commit
git add .
git commit -m "Add: your feature description"

# 9. Push to your fork
git push origin feature/your-feature-name

# 10. Create Pull Request on GitHub
```

**Contribution Areas:**
- New API providers (`apps/api/providers.py`)
- Provider manifests (`manifests/categories/`)
- Core routing improvements
- Test coverage expansion
- Documentation enhancements
- Bug fixes

**Code Style:**
- Follow PEP 8
- Use type hints
- Write docstrings
- Add tests for new features

---

## License

Open Source - See [LICENSE](LICENSE) file

---

## Links & Resources

- **Repository:** https://github.com/ujjwalredd/axiomeer
- **API Documentation:** http://localhost:8000/docs (Swagger UI)
- **Product Catalog:** [PDF Guide](docs/axiomeer_product_guide.pdf)
- **Issues:** https://github.com/ujjwalredd/axiomeer/issues
- **Discussions:** https://github.com/ujjwalredd/axiomeer/discussions

---

## Status & Metrics

- **Version:** 6.0 MVP
- **Released:** February 2026
- **Status:** Production Ready
- **Total APIs:** 91 active
- **Pass Rate:** 80.2% (73 working)
- **Categories:** 11
- **Test Coverage:** 98 tests passing
- **Docker Support:** Yes
- **Authentication:** Enterprise-ready
- **Rate Limiting:** Tier-based
- **LLM Integration:** Ollama
- **Semantic Search:** FAISS + embeddings

---

## Changelog

### v6.0 MVP (February 2026)
- Cleaned and optimized to 91 working APIs (was 107)
- Improved pass rate to 80.2% (was 69%)
- Removed 16 deprecated/broken APIs (including LibreTranslate - now requires paid API keys)
- Enterprise authentication (JWT + API keys)
- Tier-based rate limiting
- PostgreSQL database
- Docker deployment
- Comprehensive documentation

### v5.0 (January 2026)
- Added 40 new APIs (reached 100 total)
- Phase 1 & 2 API implementations
- Semantic search with FAISS
- LLM capability extraction

### v4.0 (December 2025)
- Initial public release
- 60 APIs across 6 categories
- Basic authentication
- CLI interface

---

**For support, open an issue on [GitHub](https://github.com/ujjwalredd/axiomeer/issues)**
