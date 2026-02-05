![Axiomeer](Test%20Images/Banner.png)

# Axiomeer (v5)

### The Marketplace for AI Agents

**An open marketplace where AI agents discover, evaluate, and consume tools, datasets, APIs, and other AI products -- with built-in trust, validation, and auditing.**

Think of it as an **App Store for AI**. Anyone can publish a product (a dataset, an API, a bot, a model endpoint). Any AI agent can shop the marketplace, pick the best product for the job, execute it, validate what comes back, and ingest the results -- all through a single standardized protocol.

This is not another tool-calling framework. This is **infrastructure for an AI-to-AI economy** where agents autonomously find and consume the right resources, and every transaction is verified.

> **Status: v5** -- The core pipeline works end-to-end (discover, rank, execute, validate, audit). v5 ships with **8 real providers** (weather, Wikipedia summary, country data, exchange rates, dictionary, book search, Wikidata entity search, Wikipedia dumps) -- all free, no API keys. The marketplace uses an **LLM sales agent** to produce the top 3 recommendations with tradeoffs, and clients can execute the top pick (or choose manually). Capabilities are inferred by **LLM + light heuristics** (or specified manually). Manifests auto-load on startup. The architecture is built so that **any HTTP endpoint returning structured JSON can be a product**. v5 adds **sales-agent model benchmarking**, **provider/shop caching**, **relevance scoring**, and improved **capability tags** for book and population queries. See the [Roadmap](#roadmap) and [Contributing](#contributing) sections.

**Product guide (PDF):** [Axiomeer Product Guide (PDF)](docs/axiomeer_product_guide.pdf)

![Axiomeer Demo](Test%20Images/Axiomeer.gif)

---

## Table of Contents

- [Why This Project](#why-this-project)
- [How It Differs from MCP](#how-it-differs-from-mcp)
- [The Vision](#the-vision)
- [Key Features](#key-features)
- [What's New in v5 (Feb 2026)](#whats-new-in-v5-feb-2026)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the API Server](#running-the-api-server)
- [CLI Usage](#cli-usage)
- [Publishing Apps](#publishing-apps)
- [CLI End-to-End Example](#cli-end-to-end-example)
- [API Reference](#api-reference)
- [Core Concepts](#core-concepts)
- [Configuration](#configuration)
- [Running Tests](#running-tests)
- [Demo Walkthrough](#demo-walkthrough)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Why This Project

Every AI agent needs external resources -- weather data, financial feeds, code execution, document search, translation, summarization. Today, connecting an agent to these resources means hardcoding integrations one at a time. There is no marketplace where an agent can **browse what is available, compare options, and pick the best one at runtime**.

Axiomeer solves this. It creates a **universal catalog** where:

- **Providers** publish their products (APIs, datasets, AI bots, model endpoints) with structured metadata
- **AI agents** shop the catalog based on what they need (capabilities, freshness, cost, latency)
- **The marketplace** ranks options, executes the best match, validates the output, and delivers verified results back to the agent

The trust layer is what makes this different from a simple registry:

- **If citations are required but missing** -- execution fails. No silent garbage.
- **If validation fails** (missing citations/timestamps) -- the execution is marked failed with clear errors.
- **Every execution produces a receipt** -- success or failure, with full provenance, logged and auditable.

The goal: agents that can **autonomously find and consume the right resources**, with infrastructure-level guarantees that the results are real.

---

## How It Differs from MCP

[Model Context Protocol (MCP)](https://modelcontextprotocol.io/) standardizes how an LLM connects to a **specific, pre-configured tool server**. It is a point-to-point protocol: you wire up a server, the model calls it.

Axiomeer operates at a different layer:

| | MCP | Axiomeer |
|---|---|---|
| **Scope** | Connect one model to one tool server | Connect any agent to any product in a marketplace |
| **Discovery** | The developer decides which tools are available | The agent discovers tools at runtime based on what it needs |
| **Selection** | The model picks from a fixed tool list | The marketplace ranks all available products by capability, cost, latency, freshness |
| **Trust** | No built-in output validation | Enforces citations and validates provenance |
| **Auditing** | No execution logging | Every execution logged as an immutable receipt |
| **Publishing** | Developer registers tools in config | Anyone publishes products via JSON manifests |
| **Multi-provider** | One server per integration | Multiple competing providers for the same capability |

**MCP is a protocol for tool access. This is a marketplace for tool selection.**

They are complementary. An MCP server could be one of many providers listed in the marketplace. The marketplace adds the discovery, ranking, validation, and audit layers on top.

---

## The Vision

The marketplace is designed to be the **connective layer for an AI-powered ecosystem**. The protocol is not limited to simple API calls -- it supports anything an AI agent might need:

**What can be published (the protocol supports all of these today):**
- **APIs** -- weather, finance, search, geolocation, translation, any REST endpoint
- **Datasets** -- structured data feeds, knowledge bases, document collections
- **AI Bots / Model Endpoints** -- specialized models (code generation, medical Q&A, legal research) that other agents can delegate to
- **Computation** -- code execution sandboxes, math solvers, data processing pipelines
- **Aggregators** -- products that themselves call multiple sources and return consolidated results

> v5 ships with 8 real providers across weather, search, finance, docs, and knowledge graphs. The categories above are what the architecture already supports -- contributors can add providers for any of them by writing a JSON manifest and an HTTP endpoint. See [Contributing](#contributing).

**Where this is headed:**
- An agent asks: *"I need current stock data with citations under 500ms"* -- the marketplace finds the best provider, executes it, validates the citations, and delivers verified data
- A customer builds a bot that needs weather + finance + document search -- instead of integrating three APIs manually, the bot shops the marketplace and the right providers are selected automatically
- A new provider publishes a better weather API -- every agent in the ecosystem immediately has access to it, and the router will rank it against existing options
- Providers compete on quality, latency, cost, and citation compliance -- the marketplace creates a **market for AI resources** where better products win

**The integration possibilities are open-ended.** Any HTTP endpoint that returns structured JSON with citations can be a product. The manifest is 10 lines of JSON. Publishing is a single CLI command. The marketplace handles discovery, ranking, execution, validation, and auditing.

---

## Key Features

- **Open Marketplace** -- Anyone can publish products (APIs, datasets, bots, model endpoints) via JSON manifests
- **AI-Native Discovery** -- Agents shop for products using natural language; capabilities are inferred automatically
- **Weighted Ranking** -- Scores products using capability match, latency, cost, trust, and relevance (weights configurable in `.env`)
- **Output Validation** -- Enforces citation requirements and provenance timestamps on every execution
- **Execution Receipts** -- Immutable audit log of every transaction between agents and providers
- **Provider Trust Scores** -- Success rate, citation compliance, and latency percentiles feed trust scoring
- **Relevance Scoring** -- TF‑IDF similarity between the task and app metadata improves matches
- **Strict Routing Thresholds** -- Enforces minimum relevance/coverage/score to prevent weak matches
- **Manifest Schema Validation** -- Provider manifests are validated on load and publish
- **Multi-Provider Competition** -- Multiple providers can offer the same capability; the best one wins at runtime
- **LLM Capability Inference** -- Extracts required capabilities from natural language via Ollama (LLM + light heuristics)
- **Local-First** -- Uses Ollama for local model inference; no paid API keys required
- **Idempotent Publishing** -- Manifest-based product registration, safe to retry

---

## What's New in v5 (Feb 2026)

- **Sales-agent model benchmarking** -- Local timing comparison table for small vs large models
- **Provider + shop caching** -- Short TTL caching improves repeated-query latency
- **Reliability improvements** -- Sales-agent JSON strictness + fallback repairs
- **Relevance scoring** -- TF‑IDF similarity added to ranking
- **Capability tagging fixes** -- `books` + `population` tags for better routing
- **Wikidata stability** -- User-Agent added to reduce 403s
- **CLI visibility** -- `/shop` errors surface with clear codes in CLI output

---

## Architecture Overview

```
User / Client LLM (optional)
       |
       v
+------+-------+     +-----------------+
|   CLI (Typer) | OR  | FastAPI (/docs) |
+------+-------+     +--------+--------+
       |                       |
       v                       v
+------+-----------------------+--------+
|           Marketplace Core            |
|                                       |
|  cap_extractor -> router -> sales     |
|  (infer caps)    (rank +  (Top-K +    |
|                  strict)   rationale) |
|                      -> exec          |
|                         (call +       |
|                          validate)    |
+------------------+--------------------+
                   |
       +-----------+-----------+
       |                       |
  +----+-----+          +------+------+
  |  SQLite  |          |  Providers  |
  | (apps +  |          | (HTTP APIs) |
  |  runs)   |          +-------------+
  +----------+
```

**Flow:**
1. Client sends a task (natural language or structured request)
2. Capabilities are inferred (LLM + heuristics) or specified manually
3. Router ranks registered apps against constraints **and strict thresholds**
4. Sales agent summarizes top‑K with rationale + tradeoff
5. Top app is executed via its `executor_url`
6. Output is validated (citations, timestamps)
7. A receipt is logged to SQLite regardless of outcome

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI + Uvicorn | REST API server |
| Database | SQLite + SQLAlchemy 2.0 | App catalog and run receipts |
| Data Validation | Pydantic v2 | Request/response schemas |
| CLI | Typer + Rich | Terminal interface with formatted output |
| LLM Integration | Ollama (phi3.5:3.8b) | Capability extraction and sales-agent recommendations |
| HTTP Client | Requests | Provider execution |
| Language | Python 3.10+ | Runtime |

No paid APIs are required. All LLM inference runs locally through Ollama.

---

## Repository Structure

```
.
├── apps/
│   └── api/
│       └── main.py                     # FastAPI entry point (all endpoints)
├── src/
│   └── marketplace/
│       ├── __init__.py
│       ├── settings.py                # Centralized configuration (env vars)
│       ├── cli.py                      # CLI commands: apps, shop, publish, runs
│       ├── core/
│       │   ├── cap_extractor.py       # Capability inference (LLM + heuristics)
│       │   ├── evidence_quality.py    # Deterministic quality assessment
│       │   ├── models.py             # Pydantic request/response models
│       │   ├── router.py             # Weighted recommendation engine
│       │   └── validate.py           # Output validation (citations, timestamps)
│       ├── llm/
│       │   ├── ollama_client.py       # Ollama HTTP client wrapper
│       │   └── sales_agent.py         # Top‑K rationale + tradeoff generator
│       └── storage/
│           ├── db.py                  # SQLAlchemy engine and session setup
│           ├── models.py             # AppListing ORM model
│           └── runs.py               # Run receipt ORM model
├── tests/                              # Pytest test suite
│   ├── conftest.py                    # Shared fixtures and test config
│   ├── test_api.py                    # API endpoint tests
│   ├── test_cap_extractor.py          # Capability extraction tests
│   ├── test_evidence_quality.py       # Evidence quality tests
│   ├── test_router.py                 # Recommendation engine tests
│   └── test_validate.py              # Output validation tests
├── manifests/                          # Provider manifests (auto-loaded on startup)
│   ├── realtime_weather_agent.json
│   ├── wikipedia_search.json
│   ├── rest_countries.json
│   ├── exchange_rates.json
│   ├── dictionary.json
│   ├── open_library.json
│   ├── wikidata_search.json
│   └── wikipedia_dumps.json
├── Test Images/                        # Banner assets and test results
│   ├── Axiomeer.gif
│   ├── Banner.png
│   └── v2-results/test-results.md
├── .env.example                        # Environment variable template
├── .gitignore                          # Git ignore rules
├── pyproject.toml                      # Project metadata and dependencies
└── README.md
```

---

## Prerequisites

Before setting up the project, ensure you have the following installed:

1. **Python 3.10+**
   ```bash
   python3 --version
   ```

2. **Ollama** (for LLM features: capability extraction, sales-agent recommendations)
   ```bash
   # Install Ollama: https://ollama.ai
   # Then pull the required model:
   ollama pull phi3.5:3.8b
```
   > Ollama is required for `/shop` (sales-agent recommendations) and `--auto-caps` inference. You can still list apps and query receipts without it.

3. **Git** (for cloning and contributing)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ujjwalredd/axiomeer.git
cd axiomeer
```

### 2. Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 4. Install the project in editable mode

```bash
python -m pip install -e ".[dev]"
```

This installs all dependencies:
- **Runtime:** `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `typer`, `rich`, `requests`, `python-dotenv`
- **Dev:** `pytest`, `httpx` (for API testing)

---

## Running the API Server

Start the FastAPI server:

```bash
uvicorn apps.api.main:app --reload
```

The server runs at `http://127.0.0.1:8000` by default.

- **Swagger UI (interactive docs):** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health check:** `GET /health`

The SQLite database (`marketplace.db`) is auto-created on first startup.

---

## CLI Usage

The CLI provides all marketplace operations without needing a browser. The API server must be running first.

### List all registered apps

```bash
python -m marketplace.cli apps
```

### Shop for the best tool

```bash
python -m marketplace.cli shop \
  "I need realtime weather with citations for Indianapolis" \
  --auto-caps \
  --freshness realtime \
  --citations
```

**Note:** `shop` requires a task string. If you run it without a task, it will exit with a usage hint.

**Flags:**
| Flag | Description |
|------|-------------|
| `--auto-caps` | Infer capabilities from the task using Ollama (requires Ollama running) |
| `--caps` | Manually specify capability tags (e.g., `--caps weather,realtime`) |
| `--freshness` | Require specific freshness: `static`, `daily`, or `realtime` |
| `--citations` | Require citation support (default: `True`) |
| `--max-latency-ms` | Maximum acceptable latency in milliseconds |
| `--max-cost-usd` | Maximum acceptable cost in USD |
| `--execute-top` | Execute the top recommendation immediately |

### Shop and execute the top pick

```bash
python -m marketplace.cli shop \
  "I need realtime weather with citations for Indianapolis" \
  --auto-caps \
  --freshness realtime \
  --citations \
  --execute-top
```

### View execution receipts

```bash
python -m marketplace.cli runs --n 10
```

### Fetch a full receipt by run_id

```bash
python -m marketplace.cli run 1
```

### View trust scores

```bash
python -m marketplace.cli trust
python -m marketplace.cli trust exchange_rates
```

---

## Publishing Apps

Apps are registered in the marketplace via JSON manifests.

### 1. Create a manifest file

Example: `manifests/realtime_weather_agent.json`

```json
{
  "id": "realtime_weather_agent",
  "name": "Realtime Weather Agent v2",
  "description": "Returns current weather with sources and timestamps.",
  "capabilities": ["weather", "realtime", "citations"],
  "freshness": "realtime",
  "citations_supported": true,
  "latency_est_ms": 800,
  "cost_est_usd": 0.0,
  "executor_type": "http_api",
  "executor_url": "http://127.0.0.1:8000/providers/openmeteo_weather"
}
```

**Manifest fields:**

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique app identifier |
| `name` | string | Display name |
| `description` | string | What the app does |
| `capabilities` | string[] | Tags: `weather`, `finance`, `search`, `realtime`, `citations`, `math`, `coding`, `docs`, `summarize`, `translate` |
| `freshness` | string | Data freshness: `static`, `daily`, or `realtime` |
| `citations_supported` | bool | Whether the app returns citations |
| `latency_est_ms` | int | Estimated execution latency in ms |
| `cost_est_usd` | float | Estimated cost per execution |
| `executor_type` | string | Executor protocol (currently supports `http_api` only) |
| `executor_url` | string | HTTP endpoint the marketplace calls to execute this app |

### 2. Publish to the marketplace

All manifests in `manifests/` are **auto-loaded on server startup**. To manually publish or update a listing:

```bash
python -m marketplace.cli publish manifests/realtime_weather_agent.json
```

Publishing is idempotent -- running it again updates the existing listing.
Manifests are schema-validated on load and publish; invalid manifests are rejected with clear errors.

### 3. Verify the listing

```bash
python -m marketplace.cli apps
```

---

## CLI End-to-End Example

This CLI run demonstrates the full pipeline: capability inference, marketplace ranking, and execution of the top recommendation.

```bash
python -m marketplace.cli shop \
  "What is the currency rate of usd to eur? Cite sources." \
  --auto-caps --citations --execute-top
```

**Output:**

```
Auto capabilities: ['finance', 'citations']
Status: OK
Determine the currency rate of USD to EUR.
                 Top Recommendations                 
┏━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ # ┃ app_id         ┃ name                 ┃ score ┃
┡━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ 1 │ exchange_rates │ Exchange Rate Lookup │ 0.752 │
└───┴────────────────┴──────────────────────┴───────┘

Recommendation 1: Exchange Rate Lookup (exchange_rates)
 - Capability match: 1.00 (covers ['citations', 'finance'])
 - Supports citations/provenance: yes
 - Trust score: 0.85
 - Relevance score: 0.10
 - Estimated latency: 500ms
Rationale: This app supports finance and real-time capabilities with citations, aligning perfectly for the task.
Tradeoff: Real-time data may not always be 100% accurate due to market fluctuations.

Execution result:
ok=True
Provenance:
{'sources': ['https://open.er-api.com/v6/latest/USD'], 'retrieved_at': '2026-02-05T19:35:00.028505+00:00', 'notes': []}
Output:
{'answer': 'Exchange rates for 1 USD: EUR: 0.84687. Last updated: Thu, 05 Feb 2026 00:02:31 +0000.', 'citations': ['https://open.er-api.com/v6/latest/USD'], 'retrieved_at': '2026-02-05T19:35:00.028505+00:00', 'quality': 'verified'}
```

### Strict Routing Examples (Real vs Fake)

**Real query (should succeed):**

```bash
python -m marketplace.cli shop \
  "What is the weather in Indianapolis right now? Cite sources." \
  --auto-caps --freshness realtime --citations --execute-top
```

```
Auto capabilities: ['weather', 'realtime', 'citations']
Status: OK
Current weather in Indianapolis query.
                       Top Recommendations
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ # ┃ app_id                 ┃ name                      ┃ score ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ 1 │ realtime_weather_agent │ Realtime Weather Agent v2 │ 0.751 │
└───┴────────────────────────┴───────────────────────────┴───────┘

Recommendation 1: Realtime Weather Agent v2 (realtime_weather_agent)
 - Capability match: 1.00 (covers ['citations', 'realtime', 'weather'])
 - Freshness matches requirement: realtime
 - Supports citations/provenance: yes
 - Trust score: 0.83
 - Relevance score: 0.20
Rationale: App supports required capabilities and provides real-time weather information.
Tradeoff: Estimated latency: 800ms; Estimated cost: $0.0000

Execution result:
ok=True
Provenance:
{'sources': ['https://open-meteo.com/'], 'retrieved_at': '2026-02-05T19:35:33.024257+00:00', 'notes': []}
Output:
{'answer': 'At 2026-02-05T14:30, temperature is -5.8 C, weather_code=3, wind_speed=11.1 km/h (Open-Meteo).', 'citations': ['https://open-meteo.com/'], 'retrieved_at': '2026-02-05T19:35:33.024257+00:00', 'quality': 'verified'}
```

**Fake query (should return NO_MATCH):**

```bash
python -m marketplace.cli shop \
  "Translate this sentence to Spanish: hello world. Cite sources." \
  --auto-caps --citations --execute-top
```

```
Auto capabilities: ['translate', 'citations']
Status: NO_MATCH
No apps met minimum capability coverage (1.00).
No recommendations.
```

---

## API Reference

All endpoints are available at `http://127.0.0.1:8000`. Full interactive documentation is at `/docs`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/apps` | List all registered apps |
| `POST` | `/apps` | Register a new app (409 if ID exists) |
| `GET` | `/apps/{app_id}` | Get a specific app by ID |
| `PUT` | `/apps/{app_id}` | Upsert an app (idempotent) |
| `POST` | `/shop` | Get ranked recommendations for a task |
| `POST` | `/execute` | Execute an app, validate output, log receipt |
| `GET` | `/runs` | List recent execution receipts (limit 50) |
| `GET` | `/runs/{run_id}` | Fetch a full execution receipt (including output) |
| `GET` | `/trust` | List trust scores for all apps |
| `GET` | `/apps/{app_id}/trust` | Trust score + performance stats for one app |
| `GET` | `/providers/openmeteo_weather?lat=&lon=` | Open-Meteo weather (free, no API key) |
| `GET` | `/providers/wikipedia?q={title}` | Wikipedia summary (free, no API key) |
| `GET` | `/providers/restcountries?q={name}` | Country info -- capital, population, languages (free) |
| `GET` | `/providers/exchangerate?base={currency}` | Exchange rates for 150+ currencies (free) |
| `GET` | `/providers/dictionary?word={word}` | English dictionary definitions (free) |
| `GET` | `/providers/openlibrary?q={query}` | Book search -- 20M+ titles (free) |
| `GET` | `/providers/wikidata?q={query}` | Wikidata entity search (free) |
| `GET` | `/providers/wikipedia_dumps?lang={code}` | Wikipedia dump URL for a language (free) |

### Example: Shop request

```bash
curl -X POST http://127.0.0.1:8000/shop \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Get current weather in Indianapolis",
    "required_capabilities": ["weather", "realtime"],
    "constraints": {
      "citations_required": true,
      "freshness": "realtime",
      "max_latency_ms": 2000,
      "max_cost_usd": 0.01
    }
  }'
```

**Shop response notes:**
- `recommendations` contains the ranked list with router scores.
- `sales_agent` includes the sales agent’s structured message (`summary`, `final_choice`, and top-3 `recommendations` with `rationale` + `tradeoff`).

### Example: Execute request

```bash
curl -X POST http://127.0.0.1:8000/execute \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "realtime_weather_agent",
    "task": "Current weather in Indianapolis",
    "inputs": {"lat": 39.77, "lon": -86.16},
    "require_citations": true
  }'
```

---

## Core Concepts

### Recommendation Engine

The router scores apps using **relative weights** (they are normalized by the total at runtime, so the numbers do not need to sum to 100%):

| Weight | Factor | Description |
|--------|--------|-------------|
| 0.70 | Capability Match | Coverage ratio of required vs. available capabilities |
| 0.20 | Latency | Penalizes high latency with a soft curve |
| 0.10 | Cost | Prefers cheaper without over-penalizing |
| 0.15 | Trust Score | Success rate, citation pass rate, and latency percentile |
| 0.25 | Relevance | TF‑IDF similarity between task and app metadata |

Weights are normalized by the total (sum of all weights), so the scale stays consistent.

**Strict thresholds** (apps are excluded if they fail any):
- `MIN_CAP_COVERAGE` (default 1.0)
- `MIN_RELEVANCE_SCORE` (default 0.08)
- `MIN_TOTAL_SCORE` (default 0.55)

**Hard filters** (apps are excluded if they fail any):
- Freshness mismatch
- Citations not supported (when required)
- Latency exceeds `max_latency_ms`
- Cost exceeds `max_cost_usd`

### Output Validation

When `require_citations` is true, the provider's response **must** include:
- `citations`: a non-empty list of strings (URLs or references)
- `retrieved_at`: a non-empty string (ISO timestamp)

If either is missing, the execution is marked `ok: false` with detailed `validation_errors`.

### Evidence Quality Assessment

A deterministic (no LLM) trust check:

| Quality | Condition |
|---------|-----------|
| **LOW** | `quality` field is `mock`, `simulated`, `fake`, or `test` |
| **LOW** | Answer text contains `mock data`, `simulated`, or `dummy` |
| **LOW** | No citations found |
| **HIGH** | Non-mock data with citations present |

### Execution Receipts

Every execution (success or failure) is logged to the `runs` table:
- App ID, task, citation requirement
- Success/failure status
- Full output JSON
- Validation errors (if any)
- Actual latency in milliseconds
- Timestamp
 
`/execute` now returns a `run_id` so clients can fetch the full receipt with `GET /runs/{run_id}`.

### Trust Scores

Each provider gets a trust score derived from real executions:

- **Success rate** (ok / total)
- **Citation pass rate** (ok when citations are required)
- **Latency score** (lower latency = higher score)

Scores are combined into a `trust_score` used in ranking (see `W_TRUST`). You can query:
- `GET /trust` for all apps
- `GET /apps/{app_id}/trust` for one app

---

## Configuration

All configuration is centralized in `src/marketplace/settings.py` and can be overridden via environment variables or a `.env` file.

```bash
# Copy the example and customize
cp .env.example .env
```

| Env Variable | Default Value | Description |
|-------------|--------------|-------------|
| `DATABASE_URL` | `sqlite:///./marketplace.db` | SQLAlchemy database URL |
| `API_BASE_URL` | `http://127.0.0.1:8000` | API server URL (used by CLI) |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama inference endpoint |
| `OLLAMA_TIMEOUT` | `60` | Ollama request timeout in seconds |
| `ROUTER_MODEL` | `phi3.5:3.8b` | Model for capability extraction |
| `ANSWER_MODEL` | `phi3.5:3.8b` | Reserved for grounded answer generation (not wired yet) |
| `SALES_AGENT_MODEL` | `phi3.5:3.8b` | Model for sales-agent ranking (smaller = faster) |
| `SALES_AGENT_TIMEOUT` | `60` | Sales agent request timeout in seconds |
| `W_CAP` | `0.70` | Router weight: capability match |
| `W_LAT` | `0.20` | Router weight: latency |
| `W_COST` | `0.10` | Router weight: cost |
| `W_TRUST` | `0.15` | Router weight: trust score |
| `W_REL` | `0.25` | Router weight: relevance (TF‑IDF similarity) |
| `MIN_CAP_COVERAGE` | `1.0` | Minimum required capability coverage (1.0 = all required caps) |
| `MIN_RELEVANCE_SCORE` | `0.08` | Minimum relevance score when no caps are provided |
| `MIN_TOTAL_SCORE` | `0.55` | Minimum overall score for the top candidate |
| `SALES_AGENT_TOP_K` | `8` | Max candidates passed to the sales agent |
| `SHOP_CACHE_TTL_SECONDS` | `30` | Cache TTL for `/shop` responses |
| `PROVIDER_CACHE_TTL_WEATHER` | `30` | Cache TTL for weather provider |
| `PROVIDER_CACHE_TTL_FX` | `60` | Cache TTL for exchange-rate provider |
| `PROVIDER_CACHE_TTL_WIKI` | `3600` | Cache TTL for Wikipedia summary provider |
| `PROVIDER_CACHE_TTL_WIKIDATA` | `3600` | Cache TTL for Wikidata provider |
| `PROVIDER_CACHE_TTL_WIKIDUMPS` | `3600` | Cache TTL for Wikipedia dumps provider |
| `PROVIDER_CACHE_TTL_RESTCOUNTRIES` | `3600` | Cache TTL for REST Countries provider |
| `PROVIDER_CACHE_TTL_OPENLIB` | `3600` | Cache TTL for Open Library provider |
| `PROVIDER_CACHE_TTL_DICTIONARY` | `86400` | Cache TTL for Dictionary provider |

Performance tuning tips:
- Use a smaller `SALES_AGENT_MODEL` to speed up the top-3 ranking step.
- Tune cache TTLs to trade freshness for speed (realtime apps should stay low).
- If you get frequent `NO_MATCH`, either pass explicit `--caps` or relax `MIN_CAP_COVERAGE` / `MIN_RELEVANCE_SCORE`.

## Sales-Agent Model Timing Comparison (Local Benchmark)

End-to-end timings for `python -m marketplace.cli shop ... --execute-top` on a local machine.
Same queries, same API server, only the sales-agent model changed.

**Small (current):** `phi3.5:3.8b`  
**Large (previous):** `qwen2.5:14b-instruct`  
Benchmarks below were collected on CPU.
With GPU infrastructure, you can upgrade to larger models and often improve both accuracy and response time (depending on model size and hardware).

| Query | Small Model (phi3.5:3.8b) | Large Model (qwen2.5:14b) | Delta (Large - Small) |
|---|---:|---:|---:|
| Weather Indianapolis | 18.15 | 22.70 | +4.55 |
| USD to EUR | 19.19 | 44.98 | +25.79 |
| What is Python | 21.80 | 46.92 | +25.12 |
| France population | 18.79 | 48.28 | +29.49 |
| Define serendipity | 19.13 | 27.22 | +8.09 |
| Books about Python | 19.36 | 47.46 | +28.10 |
| Wikidata entity | 20.93 | 48.71 | +27.78 |
| Wikipedia dump | 17.56 | 27.91 | +10.35 |

---

## Demo Walkthrough

This section walks through the full pipeline so contributors can see exactly what each step produces. Start the API server first, then follow along.

### Step 1: Start the server

```bash
uvicorn apps.api.main:app --reload
```

### Step 2: Publish an app to the marketplace

```bash
$ python -m marketplace.cli publish manifests/realtime_weather_agent.json

Published: realtime_weather_agent - Realtime Weather Agent v2
```

### Step 3: List the marketplace catalog

```bash
$ python -m marketplace.cli apps

                                Marketplace Apps
┏━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ id                     ┃ name                      ┃ freshness ┃ citations ┃ caps                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ dictionary             │ English Dictionary        │ static    │ yes       │ search,docs,citations      │
│ exchange_rates         │ Exchange Rate Lookup      │ realtime  │ yes       │ finance,realtime,citations │
│ wikidata_search        │ Wikidata Entity Search    │ daily     │ yes       │ rag,facts,search,citations │
│ wikipedia_dumps        │ Wikipedia Dumps (Latest)  │ daily     │ yes       │ rag,corpus,docs,citations  │
│ open_library           │ Open Library Book Search  │ daily     │ yes       │ search,docs,citations      │
│ realtime_weather_agent │ Realtime Weather Agent v2 │ realtime  │ yes       │ weather,realtime,citations │
│ rest_countries         │ REST Countries Search     │ daily     │ yes       │ search,docs,citations      │
│ wikipedia_search       │ Wikipedia Summary Search  │ daily     │ yes       │ search,docs,citations      │
└────────────────────────┴───────────────────────────┴───────────┴───────────┴────────────────────────────┘
```

### Step 4: Shop for the best tool (LLM infers capabilities)

The LLM reads the natural language query, extracts capability tags, and the router ranks all apps.

```bash
$ python -m marketplace.cli shop \
    "I need current realtime weather data for Indianapolis with citations" \
    --auto-caps --freshness realtime --citations

Auto capabilities: ['realtime', 'weather', 'citations']
Status: OK
Client requires real-time weather data with citations for Indianapolis; one candidate matches.
                       Top Recommendations
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ # ┃ app_id                 ┃ name                      ┃ score ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ 1 │ realtime_weather_agent │ Realtime Weather Agent v2 │ 0.877 │
└───┴────────────────────────┴───────────────────────────┴───────┘

Recommendation 1: Realtime Weather Agent v2 (realtime_weather_agent)
 - Capability match: 1.00 (covers ['citations', 'realtime', 'weather'])
 - Freshness matches requirement: realtime
 - Supports citations/provenance: yes
 - Trust score: 0.50
 - Relevance score: 0.10
Rationale: Capability match plus freshness and citations satisfy the request.
Tradeoff: Estimated latency: 800ms; Estimated cost: $0.0000
```

**What happened:** The LLM inferred `['realtime', 'weather', 'citations']`. The sales agent selected the weather provider and returned the recommendation rationale.

### Step 5: Shop + Execute the top pick

Adding `--execute-top` calls the provider, validates the output, and logs a receipt.

```bash
$ python -m marketplace.cli shop \
    "I need current realtime weather data for Indianapolis with citations" \
    --auto-caps --freshness realtime --citations --execute-top

...
Execution result:
ok=False
Validation errors:
 - Citations required but missing or invalid. Expected non-empty list field: citations: .
Output:
{
    'answer': 'Missing required parameters: lat and lon.',
    'citations': [],
    'retrieved_at': '2026-02-04T15:01:56.470184+00:00',
    'quality': 'verified'
}
```

**What happened:**
1. The marketplace called the Open-Meteo provider via `executor_url`
2. Output validation failed because required inputs were missing
3. `ok=False` -- execution failed
4. A receipt was logged to the `runs` table

### Step 6: Check execution receipts

Every execution (success or failure) is logged with latency and timestamp.

```bash
$ python -m marketplace.cli runs --n 5

                              Recent Runs (top 5)
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ id ┃ app_id                 ┃ ok    ┃ latency_ms ┃ created_at                       ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│  4 │ exchange_rates         │ True  │        178 │ 2026-02-05T00:22:28.809080+00:00 │
│  3 │ realtime_weather_agent │ True  │        709 │ 2026-02-05T00:19:28.952649+00:00 │
│  2 │ realtime_weather_agent │ True  │        684 │ 2026-02-04T23:53:42.891954+00:00 │
│  1 │ exchange_rates         │ True  │        305 │ 2026-02-04T23:52:47.086544+00:00 │
└────┴────────────────────────┴───────┴────────────┴──────────────────────────────────┘
```

To fetch a full receipt (including output JSON), use:

```bash
curl http://127.0.0.1:8000/runs/4
```

### Step 7: End-to-End CLI run

This runs the complete pipeline: the LLM infers capabilities, the marketplace ranks apps, and the top recommendation is executed.

```bash
$ python -m marketplace.cli shop \
    "What is the currency rate of usd to eur? Cite sources." \
    --auto-caps --citations --execute-top
```

**Output:**

```
Auto capabilities: ['finance', 'citations']
Status: OK
Currency rate of USD to EUR search task with citations.
                       Top Recommendations
┏━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ # ┃ app_id         ┃ name                      ┃ score ┃
┡━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ 1 │ exchange_rates │ Exchange Rate Lookup      │ 0.751 │
└───┴────────────────┴───────────────────────────┴───────┘

Recommendation 1: Exchange Rate Lookup (exchange_rates)
 - Capability match: 1.00 (covers ['citations', 'finance'])
 - Supports citations/provenance: yes
 - Trust score: 0.84
 - Relevance score: 0.10
 - Estimated latency: 500ms
Rationale: Provides real-time finance data, including exchange rates between currencies and supports necessary citations for the task.
Tradeoff: Estimated latency: 500ms; Estimated cost: $0.0000

Execution result:
ok=True
Provenance:
{'sources': ['https://open.er-api.com/v6/latest/USD'], 'retrieved_at': '2026-02-05T19:12:42.713038+00:00', 'notes': []}
Output:
{'answer': 'Exchange rates for 1 USD: EUR: 0.84687. Last updated: Thu, 05 Feb 2026 00:02:31 +0000.', 'citations': ['https://open.er-api.com/v6/latest/USD'], 'retrieved_at': '2026-02-05T19:12:42.713038+00:00', 'quality': 'verified'}
```

### What happens when validation fails

If citations are required but the provider does not return them, the execution is marked as failed:

```json
{
  "app_id": "some_app",
  "ok": false,
  "output": {"answer": "Some data without citations"},
  "provenance": null,
  "validation_errors": [
    "Citations required but missing or invalid. Expected non-empty list field: citations: [str].",
    "Citations required but retrieved_at timestamp is missing."
  ]
}
```

### Pipeline summary

| Step | Component | What happens | Decision point |
|------|-----------|-------------|----------------|
| 1 | `cap_extractor` | LLM + heuristics infer capabilities from natural language | -- |
| 2 | `router` | Rank apps by capability, latency, cost, trust, and relevance (hard filters plus minimum coverage/relevance/score thresholds) | NO_MATCH if nothing passes filters |
| 3 | Execute | Call provider's `executor_url`, get JSON response | Fail if provider unreachable |
| 4 | `validate` | Check citations list and `retrieved_at` timestamp | `ok=false` if validation fails |
| 5 | `runs` table | Log receipt (app_id, task, ok, latency, errors, timestamp) | Always logged |

---

## Roadmap

- [x] ~~Add test suite (pytest) -- 83 tests~~
- [x] ~~Move configuration to environment variables / `.env` file~~
- [x] ~~Replace mock providers with 8 real free-API providers~~
- [x] ~~Auto-bootstrap manifests on startup~~
- [x] ~~Fix execute pipeline (forward inputs to providers)~~
- [ ] **Evidence-quality + grounded answers** -- Reintroduce deterministic evidence scoring and grounded response generation when citations are strong
- [ ] **Manifest hosting** -- Migrate manifests from local JSON files to MongoDB (or PostgreSQL) so providers can be registered, discovered, and managed remotely. This enables real-world deployment where multiple instances share a central registry.
- [ ] **Cloud deployment** -- Dockerize the API and deploy to a cloud provider (AWS/GCP/Railway) with a persistent database, making the marketplace accessible for real-world integration testing.
- [ ] **Improved LLM support** -- Support larger models (Mistral, Llama 3, GPT-4o) via configurable model backends. Add model benchmarking to compare grounding accuracy across model sizes.
- [ ] **Structured input extraction** -- Use the LLM to extract structured query parameters from natural language (e.g., "weather in Tokyo" -> `{"lat": 35.68, "lon": 139.69}`) instead of passing empty inputs.
- [ ] **Multi-tool plans** -- Let the LLM chain multiple providers in sequence (e.g., search country -> get exchange rate for that country's currency).
- [x] ~~Trust scores per provider~~ -- Track failure rate, latency percentiles, and citation compliance over time. Use scores to improve routing.
- [ ] **Authentication and API keys** -- Add API key gating so third-party providers can register securely.
- [ ] **Manifest validation** -- JSON schema + allowlist enforcement for provider registration.

---

## v5 Changes

- **Sales-agent benchmarking** table (small vs large model timing)
- **Provider + shop response caching** for faster repeated runs
- **Capability tag fixes** for books + population queries
- **Sales-agent JSON reliability** improvements
- **Provider set remains 8 free sources** (no paid APIs)
- **Trust scores + audit receipts** (run_id + /runs/{id} detail)
- **Manifest schema validation** on bootstrap and publish
---

## Contributing

Contributions are welcome. Here is how to get started:

### 1. Fork and clone

```bash
git clone https://github.com/ujjwalredd/axiomeer.git
cd axiomeer
```

### 2. Set up the development environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

### 3. Run the test suite

```bash
pytest -v
```

All tests should pass before making any changes. Example output from a recent run:

```
69 passed in 2.35s
```

Use `pytest -m "not integration"` to run without network access.

### 4. Start the API server

```bash
uvicorn apps.api.main:app --reload
```

### 5. Verify apps are auto-loaded and test the flow

```bash
python -m marketplace.cli apps                                          # all 8 manifests auto-loaded
python -m marketplace.cli shop "weather" --auto-caps --execute-top      # shop + execute
python -m marketplace.cli runs                                          # check audit log
```

### 6. Make your changes

Key areas where contributions are needed:

| Area | Directory | Description |
|------|-----------|-------------|
| New providers | `apps/api/main.py` | Add new `/providers/*` endpoints |
| New app manifests | `manifests/` | Create JSON manifests for new tools |
| Core logic | `src/marketplace/core/` | Improve routing, validation, or quality assessment |
| Storage | `src/marketplace/storage/` | Database models and queries |
| CLI | `src/marketplace/cli.py` | New commands or improved output |
| LLM integration | `src/marketplace/llm/` | Support additional model backends |
| Tests | `tests/` | Expand pytest coverage for new features |

### 7. Submit a pull request

- Create a feature branch: `git checkout -b feature/your-feature-name`
- Commit your changes with clear messages
- Push and open a PR against `main`

---

## License

This project is open source. See the [LICENSE](LICENSE) file for details.
