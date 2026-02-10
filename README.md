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
# Clone and start
git clone https://github.com/ujjwalredd/Axiomeer.git
cd Axiomeer
docker-compose up -d

# Verify
curl http://localhost:8000/health
# {"status":"ok"}

curl http://localhost:8000/apps | jq 'length'
# 91
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
| Test Coverage | 47/47 passing |

---

## Project Structure

```
├── apps/api/main.py          # FastAPI application (1200+ lines)
├── src/marketplace/
│   ├── core/
│   │   ├── router.py         # Weighted ranking algorithm
│   │   └── semantic_search.py # FAISS vector search
│   ├── auth/
│   │   ├── security.py       # JWT + bcrypt + API keys
│   │   └── rate_limiter.py   # Tier-based rate limiting
│   └── storage/
│       ├── db.py             # SQLAlchemy setup
│       └── users.py          # User/APIKey models
├── sdk/python/               # PyPI package
├── manifests/                # 91 API definitions
└── docker-compose.yml        # PostgreSQL + API
```

---

## Run Tests

```bash
# All tests
pytest tests/ -v

# Health check all 91 APIs
python scripts/api_health_check.py
```

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
