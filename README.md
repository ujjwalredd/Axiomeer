![Axiomeer](Test%20Images/Banner.png)

# Axiomeer v6

AI marketplace platform for autonomous agent resource discovery and execution.

![Demo](Test%20Images/Axiomeer.gif)

## Overview

Axiomeer provides a marketplace protocol where AI agents discover, evaluate, and consume external resources (APIs, datasets, models) through weighted ranking, validation, and provenance tracking.

**Status:** v6.0 (Feb 2026) - Production prototype
**Catalog:** 60 products, 52 provider endpoints, 9 categories
**Infrastructure:** 100% free APIs, local LLM inference

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Client (CLI / API / Agent)                            │
└─────────────────────┬───────────────────────────────────┘
                      │
           ┌──────────▼──────────┐
           │  /shop Endpoint     │
           └──────────┬──────────┘
                      │
        ┌─────────────▼─────────────┐
        │  Capability Extraction    │  ← Ollama LLM
        └─────────────┬─────────────┘
                      │
    ┌─────────────────▼─────────────────┐
    │  Router (Weighted Ranking)        │
    │  - Semantic Search (FAISS)        │
    │  - TF-IDF Fallback                │
    │  - Capability Match: 70%          │
    │  - Relevance: 25%                 │
    │  - Trust: 15%, Latency: 20%       │
    └─────────────┬─────────────────────┘
                  │
       ┌──────────▼──────────┐
       │  Sales Agent (LLM)  │
       └──────────┬──────────┘
                  │
      ┌───────────▼───────────┐
      │  /execute Endpoint    │
      └───────────┬───────────┘
                  │
    ┌─────────────▼─────────────┐
    │  Provider HTTP Call       │
    └─────────────┬─────────────┘
                  │
       ┌──────────▼──────────┐
       │  Output Validation  │  ← Citations, Timestamps
       └──────────┬──────────┘
                  │
          ┌───────▼────────┐
          │  Receipt (DB)  │  ← Provenance Log
          └────────────────┘
```

**Flow:** Client → Shop → Capability Extraction → Router (Semantic/TF-IDF) → Sales Agent → Execute → Provider → Validation → Receipt

## Core Components

**Router:** Scores products using normalized weights (capability 0.70, relevance 0.25, trust 0.15, latency 0.20, cost 0.10)

**Semantic Search:** Optional vector-based matching (sentence-transformers + FAISS), falls back to TF-IDF

**Validation Layer:** Enforces citation presence, timestamp format, quality assessment

**Trust Tracking:** Success rate, citation compliance, latency percentiles per provider

**Execution Receipts:** Immutable logs with full provenance (app_id, task, output, validation, timestamps)

## Technical Stack

| Component | Technology |
|-----------|-----------|
| API | FastAPI, Uvicorn, Pydantic v2 |
| Database | SQLite (dev), PostgreSQL compatible |
| LLM | Ollama (phi3.5:3.8b default) |
| Semantic Search | sentence-transformers, FAISS |
| Relevance | scikit-learn (TF-IDF) |
| CLI | Typer, Rich |
| Runtime | Python 3.10+ |

## Installation

```bash
# Clone and setup
git clone https://github.com/ujjwalredd/axiomeer.git
cd axiomeer
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux

# Install
pip install --upgrade pip
pip install -e ".[dev]"

# Install Ollama
# macOS: brew install ollama
# Linux: curl -fsSL https://ollama.com/install.sh | sh
ollama pull phi3.5:3.8b

# Optional: Semantic search
pip install faiss-cpu sentence-transformers

# Start server
uvicorn apps.api.main:app --reload
```

## Quick Start

```bash
# List products
python -m marketplace.cli apps

# Search with capability inference
python -m marketplace.cli shop \
  "Current weather in Indianapolis with citations" \
  --auto-caps \
  --execute-top

# Manual capabilities
python -m marketplace.cli shop \
  "Bitcoin price" \
  --caps finance,citations \
  --max-latency-ms 2000 \
  --execute-top

# View receipts
python -m marketplace.cli runs --n 10

# Check trust scores
python -m marketplace.cli trust
```

## API Reference

**Base URL:** `http://127.0.0.1:8000`

### Endpoints

```
GET  /health                    → {"status": "ok"}
GET  /apps                      → List all products
GET  /apps/{app_id}             → Get product details
POST /apps                      → Register product (409 if exists)
PUT  /apps/{app_id}             → Upsert product
POST /shop                      → Get recommendations
POST /execute                   → Execute product
GET  /runs                      → List receipts (limit 50)
GET  /runs/{run_id}             → Get full receipt
GET  /trust                     → All trust scores
GET  /apps/{app_id}/trust       → Product trust score
GET  /semantic-search/stats     → Semantic search status
```

### Shop Request

```json
POST /shop
{
  "task": "Get current weather in Indianapolis",
  "required_capabilities": ["weather", "realtime"],
  "constraints": {
    "citations_required": true,
    "freshness": "realtime",
    "max_latency_ms": 2000,
    "max_cost_usd": 0.01
  }
}
```

### Shop Response

```json
{
  "status": "OK",
  "recommendations": [
    {
      "app_id": "realtime_weather_agent",
      "score": 0.752,
      "capability_match": 1.0,
      "trust_score": 0.50,
      "relevance_score": 0.40
    }
  ],
  "metrics": {
    "total_time_ms": 245,
    "semantic_search_time_ms": 120,
    "semantic_search_used": true
  }
}
```

### Execute Request

```json
POST /execute
{
  "app_id": "realtime_weather_agent",
  "task": "Current weather",
  "inputs": {"lat": 39.77, "lon": -86.16},
  "require_citations": true
}
```

### Execute Response

```json
{
  "ok": true,
  "run_id": 42,
  "output": {
    "answer": "Temperature 1.0°C, wind 17.6 km/h",
    "citations": ["https://open-meteo.com/"],
    "retrieved_at": "2026-02-07T00:00:00+00:00",
    "quality": "verified"
  },
  "latency_ms": 910,
  "validation_errors": []
}
```

## Configuration

Environment variables in `.env`:

```bash
# Database
DATABASE_URL=sqlite:///./marketplace.db
API_BASE_URL=http://127.0.0.1:8000

# LLM
OLLAMA_URL=http://localhost:11434/api/generate
ROUTER_MODEL=phi3.5:3.8b
SALES_AGENT_MODEL=phi3.5:3.8b

# Router Weights (normalized at runtime)
W_CAP=0.70      # Capability match
W_REL=0.25      # Relevance (semantic/TF-IDF)
W_TRUST=0.15    # Trust score
W_LAT=0.20      # Latency penalty
W_COST=0.10     # Cost consideration

# Thresholds
MIN_CAP_COVERAGE=1.0     # 100% coverage required
MIN_RELEVANCE_SCORE=0.08
MIN_TOTAL_SCORE=0.55

# Semantic Search
SEMANTIC_SEARCH_ENABLED=true
SEMANTIC_SEARCH_TOP_K=20
SEMANTIC_SEARCH_MODEL=all-MiniLM-L6-v2

# Caching (seconds)
SHOP_CACHE_TTL_SECONDS=30
PROVIDER_CACHE_TTL_WEATHER=30
PROVIDER_CACHE_TTL_FX=60
PROVIDER_CACHE_TTL_WIKI=3600
```

## Testing

### Unit Tests

```bash
pytest -v                        # All tests
pytest -m "not integration"      # Offline tests only
```

69 tests covering API endpoints, capability extraction, router logic, validation, and evidence quality.

### Benchmark Tests

```bash
# Start server
uvicorn apps.api.main:app --reload

# Run benchmarks (requires server)
pytest tests/test_benchmarks.py -v
```

**Test Categories:**

1. **Real API Validation:** Verify genuine data retrieval with citations
2. **Fake Query Rejection:** Demonstrate NO_MATCH for impossible/non-existent capabilities
3. **Latency Benchmarks:** Measure semantic search, endpoint, and end-to-end performance
4. **Citation Validation:** Enforce citation requirements and quality checks
5. **Trust Scoring:** Verify score calculation and updates
6. **Provenance Tracking:** Validate execution receipt logging

**Expected Results:**

- Semantic search: <50ms average
- Health endpoint: <10ms
- Shop endpoint: 100-300ms (includes LLM inference)
- Execute endpoint: 500-2000ms (varies by provider)
- Fake queries: NO_MATCH in <200ms
- Citation validation: 100% enforcement

### Integration Testing

```bash
# Test full pipeline
python -m marketplace.cli shop \
  "weather in Tokyo" \
  --auto-caps \
  --execute-top

# Verify receipt
python -m marketplace.cli runs --n 1

# Check trust score
python -m marketplace.cli trust realtime_weather_agent
```

## Publishing Products

### Manifest Schema

```json
{
  "id": "product_id",
  "name": "Display Name",
  "description": "What it does",
  "category": "utilities",
  "capabilities": ["weather", "realtime", "citations"],
  "freshness": "realtime",
  "citations_supported": true,
  "latency_est_ms": 800,
  "cost_est_usd": 0.0,
  "executor_type": "http_api",
  "executor_url": "http://127.0.0.1:8000/providers/endpoint"
}
```

### Provider Response

```json
{
  "answer": "Response content",
  "citations": ["https://source.com"],
  "retrieved_at": "2026-02-07T00:00:00+00:00",
  "quality": "verified"
}
```

### Publishing

```bash
# Auto-load: Place in manifests/categories/
# Manual: python -m marketplace.cli publish manifest.json
```

## Product Catalog

**60 products across 9 categories:**

- Government Data (11): NASA, Census, World Bank, FRED, COVID-19
- Knowledge (8): arXiv, PubMed, Semantic Scholar, Wikidata
- Financial (3): CoinGecko, Coinbase, Blockchain.com
- Geographic (3): OpenStreetMap, GeoNames, IP Geolocation
- Media (6): OMDB, Unsplash, Pexels, Genius
- Language (2): LibreTranslate, Datamuse
- Utilities (7): Random User, QR Generator, JokeAPI
- AI Models (12): GPT-2, BERT, Llama 3, Mistral, Sentiment Analysis
- General (8): Weather, Wikipedia, Countries, Exchange Rates

All products use free APIs. See docs/axiomeer_product_guide.pdf for complete catalog.

## Performance

**Benchmark Results:**

| Metric | Value |
|--------|-------|
| Products | 60 |
| Provider Endpoints | 52 |
| Test Success Rate | 100% (69/69 unit tests) |
| Semantic Search | <50ms average |
| Shop Query | 100-300ms |
| Provider Execution | 500-2000ms (external API dependent) |
| Health Check | <10ms |
| Database | SQLite (single-node), PostgreSQL ready |

**Latency by Category:**

- System operations: <5ms
- Media APIs: <50ms
- Financial APIs: 100-300ms
- Knowledge APIs: 1-4s (large databases)
- Geographic APIs: 3-6s (geospatial queries)

## Production Deployment

### Docker

```dockerfile
FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN pip install -e .
EXPOSE 8000
CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Multi-Worker

```bash
uvicorn apps.api.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --log-level info
```

### PostgreSQL

```bash
export DATABASE_URL=postgresql://user:pass@host:5432/axiomeer
```

## Security

- Input validation via Pydantic schemas
- Citation URL validation
- Timestamp format verification
- SQL injection prevention (SQLAlchemy ORM)
- No arbitrary code execution
- Provider isolation (HTTP-only execution)

## Troubleshooting

**Server won't start:**
```bash
lsof -i :8000  # Check port
uvicorn apps.api.main:app --port 8001  # Use different port
```

**Ollama connection failed:**
```bash
ollama serve  # Start Ollama
curl http://localhost:11434/api/tags  # Verify
```

**Semantic search unavailable:**
```bash
pip install faiss-cpu sentence-transformers
# Or: export SEMANTIC_SEARCH_ENABLED=false
```

**NO_MATCH results:**
```bash
export MIN_CAP_COVERAGE=0.8  # Relax threshold
export MIN_RELEVANCE_SCORE=0.05
```

## Documentation

- [Product Guide (PDF)](docs/axiomeer_product_guide.pdf) - Complete documentation
- [API Docs](http://127.0.0.1:8000/docs) - Interactive Swagger UI
- [Repository Structure](#repository-structure) - See below

## Repository Structure

```
.
├── apps/
│   └── api/
│       ├── main.py              # FastAPI server
│       └── providers.py         # 52 provider endpoints
├── src/marketplace/
│   ├── core/
│   │   ├── router.py            # Weighted ranking
│   │   ├── semantic_search.py   # FAISS + embeddings
│   │   ├── cap_extractor.py     # LLM capability inference
│   │   ├── validate.py          # Output validation
│   │   └── models.py            # Pydantic schemas
│   ├── llm/
│   │   ├── ollama_client.py     # LLM client
│   │   └── sales_agent.py       # Recommendation explanation
│   ├── storage/
│   │   ├── db.py                # Database setup
│   │   ├── models.py            # ORM models
│   │   └── runs.py              # Receipt storage
│   ├── cli.py                   # CLI commands
│   └── settings.py              # Configuration
├── tests/
│   ├── test_api.py              # API tests
│   ├── test_router.py           # Router tests
│   ├── test_benchmarks.py       # Benchmark suite
│   └── ...
├── manifests/categories/        # Product manifests
│   ├── ai_models/
│   ├── financial/
│   ├── government_data/
│   └── ...
└── docs/
    └── axiomeer_product_guide.pdf
```

## Contributing

```bash
# Setup
git clone https://github.com/ujjwalredd/axiomeer.git
cd axiomeer
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Test
pytest -v

# Run server
uvicorn apps.api.main:app --reload

# Verify
python -m marketplace.cli apps
python -m marketplace.cli shop "test query" --auto-caps

# Submit PR
git checkout -b feature/your-feature
git commit -m "Description"
git push origin feature/your-feature
```

**Contribution Areas:**

- New providers (apps/api/providers.py)
- Product manifests (manifests/categories/)
- Core logic (src/marketplace/core/)
- Tests (tests/)
- Documentation

## License

Open source. See LICENSE file.

---

**Version:** 6.0
**Released:** February 2026
**Status:** Production Prototype
**Repository:** https://github.com/ujjwalredd/axiomeer
