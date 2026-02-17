# Axiomeer

**The Universal Marketplace for AI Agents**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![PyPI](https://img.shields.io/pypi/v/axiomeer.svg)](https://pypi.org/project/axiomeer/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

One API to access 91+ services. Search with natural language. Execute with 3 lines of code.

```python
from axiomeer import AgentMarketplace

client = AgentMarketplace(api_key="axm_xxx")
result = client.shop("get weather in Tokyo")
```

![Demo](Test%20Images/Axiomeer.gif)

---

## Features

| Feature | Description |
|---------|-------------|
| **91+ APIs** | Weather, finance, search, translations, and more |
| **Semantic Search** | FAISS vector search with 384-dim embeddings |
| **Natural Language** | Ask in plain English, get the right API |
| **Manifest Schema** | `http_method` (GET/POST) + `input_schema` for LLM parameter extraction |
| **Retry Logic** | Automatic retry with backoff on transient provider failures |
| **Python SDK** | `pip install axiomeer` |
| **Enterprise Auth** | JWT + API keys + rate limiting |

---

## Tech Stack

**Backend:** FastAPI, PostgreSQL, Pydantic v2, SQLAlchemy

**AI/ML:** FAISS, sentence-transformers (all-MiniLM-L6-v2), Ollama

**Security:** JWT (HMAC-SHA256), bcrypt (cost 12), SHA-256 API key hashing

**Infrastructure:** Docker, Alembic migrations

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                        AI AGENT                              │
│            "I need current weather data"                     │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                    AXIOMEER API                              │
│                                                              │
│   ┌─────────────────┐    ┌─────────────────┐                 │
│   │ Semantic Search │    │  LLM Capability │                 │
│   │ (FAISS 384-dim) │    │   Extraction    │                 │
│   └─────────────────┘    └─────────────────┘                 │
│                                                              │
│   ┌─────────────────────────────────────────┐                │
│   │         Weighted Ranking                 │               │
│   │  capability(70%) + relevance(25%)        │               │
│   │  + trust(15%) - latency(20%) - cost(10%) │               │
│   └─────────────────────────────────────────┘                │
│                                                              │
│   ┌─────────────────────────────────────────┐                │
│   │     91 APIs across 14 categories         │               │
│   └─────────────────────────────────────────┘                │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
              Ranked API recommendations
```

---

## Quick Start

```bash
# Clone and start with Docker (PostgreSQL + Redis + API)
git clone https://github.com/ujjwalredd/Axiomeer.git
cd Axiomeer
cp .env.example .env
# Edit .env: set DB_PASSWORD=your_secure_password
docker-compose up -d

# Verify (first startup may take ~2 min for semantic search model)
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/apps | jq 'length'
# 91
```

**Docker services:** PostgreSQL (port 5433), Redis (6379), API (8000). Auth disabled by default for easy access.

### API Documentation

When the server is running:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### cURL Examples

```bash
# Shop (find APIs by natural language)
curl -X POST http://localhost:8000/shop \
  -H "Content-Type: application/json" \
  -d '{"task": "get weather in Tokyo"}'

# Versioned endpoint
curl -X POST http://localhost:8000/v1/shop \
  -H "Content-Type: application/json" \
  -d '{"task": "translate text to Spanish"}'

# Execute an API
curl -X POST http://localhost:8000/execute \
  -H "Content-Type: application/json" \
  -d '{"app_id": "realtime_weather_agent", "task": "weather in NYC", "inputs": {"lat": 40.7, "lon": -74.0}}'

# Export tool schemas for OpenAI/Anthropic function calling
curl "http://localhost:8000/v1/tools/schemas?format=openai"
curl "http://localhost:8000/v1/tools/schemas?format=anthropic"

# Usage dashboard (requires auth)
curl "http://localhost:8000/v1/dashboard/usage?hours=24" \
  -H "Authorization: Bearer <token>"
```

### Node.js / fetch Example

```javascript
// Shop for APIs
const shop = await fetch("http://localhost:8000/shop", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ task: "get weather in Tokyo" }),
}).then((r) => r.json());

// Execute
const exec = await fetch("http://localhost:8000/execute", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    app_id: shop.recommendations[0]?.app_id || "realtime_weather_agent",
    task: "weather in NYC",
    inputs: { lat: 40.7, lon: -74.0 },
  }),
}).then((r) => r.json());
```

### Get an API Key

```bash
# Sign up
curl -X POST http://localhost:8000/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "username": "testuser", "password": "password123"}'

# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
# Save the access_token

# Create API key
curl -X POST http://localhost:8000/auth/api-keys \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Key"}'
# Returns: axm_xxxxx
```

### Use the SDK

```bash
pip install axiomeer
```

```python
from axiomeer import AgentMarketplace

# Initialize
client = AgentMarketplace(api_key="axm_xxxxx")

# Find the right API using natural language
result = client.shop("translate text to Spanish")

# Execute it
execution = result.execute(client, text="Hello world", target="es")
print(execution.result)
```

---

## API Categories

| Category | Count | Examples |
|----------|-------|----------|
| Knowledge | 12 | Wikipedia, arXiv, PubMed |
| Government | 11 | NASA, World Bank, Census |
| Utilities | 14 | UUID, QR codes, Base64 |
| Media | 6 | Unsplash, TMDB, Pexels |
| Language | 6 | Dictionary, Translations |
| Geographic | 4 | IP location, Countries |
| Science | 5 | Math, Periodic table |
| Finance | 3 | Exchange rates, Crypto |
| Entertainment | 5 | Pokemon, Movies |
| + 5 more | 25 | ... |

**Total: 91 APIs**

---

## Manifest Format

Manifests support optional `http_method` and `input_schema` for smarter execution:

```json
{
  "id": "realtime_weather_agent",
  "name": "Realtime Weather Agent",
  "executor_url": "http://127.0.0.1:8000/providers/openmeteo_weather",
  "http_method": "GET",
  "input_schema": {
    "parameters": ["lat", "lon", "timezone_name"],
    "examples": "\"Weather in Tokyo\" → {\"lat\": 35.67, \"lon\": 139.65}"
  }
}
```

- **http_method**: `GET` (default) or `POST` for provider calls
- **input_schema**: Enables LLM to extract parameters from natural language tasks

---

## Security

| Feature | Implementation |
|---------|---------------|
| Authentication | JWT with HMAC-SHA256 (60-min expiry) |
| API Keys | SHA-256 hashed, `axm_` prefix |
| Passwords | bcrypt with cost factor 12 |
| Rate Limiting | Tier-based (100/1000/10000 req/hr) |

---

## Performance

| Metric | Value |
|--------|-------|
| API Response (p50) | 145ms |
| API Response (p95) | 387ms |
| Throughput | 2,034 req/sec |
| Test Coverage | 69+ tests passing |

---

---

## Project Structure

```
├── apps/api/
│   ├── main.py               # FastAPI application
│   ├── providers.py          # 50+ provider endpoints
│   ├── auth_routes.py        # Auth & API key routes
│   └── routers/
│       └── v1.py             # /v1/* (schemas, dashboard, shop, execute, apps)
├── src/marketplace/
│   ├── core/
│   │   ├── router.py         # Weighted ranking algorithm
│   │   ├── semantic_search.py # FAISS vector search
│   │   ├── executor.py       # Async HTTP executor (httpx + retry)
│   │   ├── cache.py          # Redis + in-memory cache
│   │   └── llm.py            # Parameter extraction from manifests
│   ├── auth/
│   │   ├── security.py       # JWT + bcrypt + API keys
│   │   └── rate_limiter.py   # Tier-based rate limiting
│   └── storage/
│       ├── db.py             # SQLAlchemy setup
│       └── users.py          # User/APIKey models
├── sdk/python/               # PyPI package
├── manifests/                # 91 API definitions (with http_method, input_schema)
├── scripts/
│   ├── validate_manifests.py # Validate manifests against schema
│   └── api_health_check.py   # Health check all APIs
├── .env.example              # Required environment variables
└── docker-compose.yml        # PostgreSQL + API
```

---

## Run Tests

```bash
# All tests
pytest tests/ -v

# Validate manifests (91 API definitions)
python scripts/validate_manifests.py

# Health check all 91 APIs
python scripts/api_health_check.py
```

---

## SDK Examples

See `sdk/python/examples/` for:
- `basic_usage.py` - Shop, execute, list apps
- `advanced_usage.py` - Capabilities, constraints, error handling

---

## SDK

**PyPI:** [pypi.org/project/axiomeer](https://pypi.org/project/axiomeer/)

```bash
pip install axiomeer
```

```python
from axiomeer import AgentMarketplace, RateLimitError

client = AgentMarketplace(api_key="axm_xxx")

# Shop for tools
result = client.shop("I need weather data")
print(result.selected_app.name)
print(result.confidence)

# Execute
execution = result.execute(client, location="NYC")

# Error handling
try:
    result = client.shop("query")
except RateLimitError as e:
    print(f"Retry after {e.retry_after}s")
```

---

## License

MIT

---

## Contact

**Ujjwal Reddy** - [ujjwalreddyks@gmail.com](mailto:ujjwalreddyks@gmail.com)

GitHub: [@ujjwalredd](https://github.com/ujjwalredd)
