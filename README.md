# Axiomeer (v1)

### The Marketplace for AI Agents

**Status (v1): Prototype / reference implementation**
Axiomeer ships the full marketplace loop — **publish → shop → execute → validate → receipts → abstain** — and includes a mix of **demo providers** plus a **real provider example (Open-Meteo)**.  
The core value is the routing + trust + auditing layer; the marketplace becomes “real” as the community adds more providers.

Think of it as an **App Store for AI**. Anyone can publish a product (a dataset, an API, a bot, a model endpoint). Any AI agent can shop the marketplace, pick the best product for the job, execute it, validate what comes back, and ingest the results -- all through a single standardized protocol.

This is not another tool-calling framework. This is **infrastructure for an AI-to-AI economy** where agents autonomously find and consume the right resources, and every transaction is verified.

![Axiomeer Demo](Test%20Images/Axiomeer.gif)

---

## Table of Contents

- [Why This Project](#why-this-project)
- [How It Differs from MCP](#how-it-differs-from-mcp)
- [The Vision](#the-vision)
- [Key Features](#key-features)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Running the API Server](#running-the-api-server)
- [CLI Usage](#cli-usage)
- [Publishing Apps](#publishing-apps)
- [Client LLM Simulation](#client-llm-simulation)
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
- **If evidence quality is LOW** (mock/simulated) -- the agent abstains rather than hallucinating a confident wrong answer.
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
| **Trust** | No built-in output validation | Enforces citations, validates provenance, assesses evidence quality |
| **Auditing** | No execution logging | Every execution logged as an immutable receipt |
| **Publishing** | Developer registers tools in config | Anyone publishes products via JSON manifests |
| **Multi-provider** | One server per integration | Multiple competing providers for the same capability |

**MCP is a protocol for tool access. This is a marketplace for tool selection.**

They are complementary. An MCP server could be one of many providers listed in the marketplace. The marketplace adds the discovery, ranking, validation, and audit layers on top.

---

## The Vision

The marketplace is designed to be the **connective layer for an AI-powered ecosystem**. The products in the catalog are not limited to simple API calls -- they can be anything an AI agent might need:

**What can be published:**
- **APIs** -- weather, finance, search, geolocation, translation, any REST endpoint
- **Datasets** -- structured data feeds, knowledge bases, document collections
- **AI Bots / Model Endpoints** -- specialized models (code generation, medical Q&A, legal research) that other agents can delegate to
- **Computation** -- code execution sandboxes, math solvers, data processing pipelines
- **Aggregators** -- products that themselves call multiple sources and return consolidated results

**What this enables:**
- An agent asks: *"I need current stock data with citations under 500ms"* -- the marketplace finds the best provider, executes it, validates the citations, and delivers verified data
- A customer builds a bot that needs weather + finance + document search -- instead of integrating three APIs manually, the bot shops the marketplace and the right providers are selected automatically
- A new provider publishes a better weather API -- every agent in the ecosystem immediately has access to it, and the router will rank it against existing options
- Providers compete on quality, latency, cost, and citation compliance -- the marketplace creates a **market for AI resources** where better products win

**The integration possibilities are open-ended.** Any HTTP endpoint that returns structured JSON with citations can be a product. The manifest is 10 lines of JSON. Publishing is a single CLI command. The marketplace handles discovery, ranking, execution, validation, and auditing.

---

## Key Features

- **Open Marketplace** -- Anyone can publish products (APIs, datasets, bots, model endpoints) via JSON manifests
- **AI-Native Discovery** -- Agents shop for products using natural language; capabilities are inferred automatically
- **Weighted Ranking** -- Scores products using capability match (70%), latency (20%), and cost (10%) with hard constraint filtering
- **Output Validation** -- Enforces citation requirements and provenance timestamps on every execution
- **Evidence Quality Assessment** -- Deterministic (no LLM) quality scoring prevents agents from trusting mock/fake data
- **Execution Receipts** -- Immutable audit log of every transaction between agents and providers
- **Multi-Provider Competition** -- Multiple providers can offer the same capability; the best one wins at runtime
- **Graceful Abstention** -- When evidence is insufficient, agents abstain instead of hallucinating
- **LLM Capability Inference** -- Extracts required capabilities from natural language via Ollama + heuristic fallbacks
- **Local-First** -- Uses Ollama for local model inference; no paid API keys required
- **Idempotent Publishing** -- Manifest-based product registration, safe to retry

---

## Architecture Overview

```
User / LLM Client
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
|  cap_extractor  ->  router  ->  exec  |
|  (infer caps)     (rank)     (call +  |
|                              validate)|
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
3. Router ranks registered apps against constraints
4. Top app is executed via its `executor_url`
5. Output is validated (citations, timestamps) and quality-assessed
6. A receipt is logged to SQLite regardless of outcome

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| API Framework | FastAPI + Uvicorn | REST API server |
| Database | SQLite + SQLAlchemy 2.0 | App catalog and run receipts |
| Data Validation | Pydantic v2 | Request/response schemas |
| CLI | Typer + Rich | Terminal interface with formatted output |
| LLM Integration | Ollama (llama2:7b) | Capability extraction and answer generation |
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
│       ├── client_llm.py              # End-to-end LLM client simulation
│       ├── core/
│       │   ├── cap_extractor.py       # Capability inference (LLM + heuristics)
│       │   ├── evidence_quality.py    # Deterministic quality assessment
│       │   ├── models.py             # Pydantic request/response models
│       │   ├── router.py             # Weighted recommendation engine
│       │   └── validate.py           # Output validation (citations, timestamps)
│       ├── llm/
│       │   └── ollama_client.py       # Ollama HTTP client wrapper
│       └── storage/
│           ├── db.py                  # SQLAlchemy engine and session setup
│           ├── models.py             # AppListing ORM model
│           └── runs.py               # Run receipt ORM model
├── tests/                              # Pytest test suite
│   ├── test_api.py                    # API endpoint tests
│   ├── test_cap_extractor.py          # Capability extraction tests
│   ├── test_evidence_quality.py       # Evidence quality tests
│   ├── test_router.py                 # Recommendation engine tests
│   └── test_validate.py              # Output validation tests
├── manifests/
│   └── realtime_weather_agent.json    # Example app manifest
├── Test Images/                        # Demo screenshots
├── .env.example                        # Environment variable template
├── marketplace.db                      # SQLite database (auto-created)
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

2. **Ollama** (for LLM features: capability extraction, answer generation)
   ```bash
   # Install Ollama: https://ollama.ai
   # Then pull the required model:
   ollama pull llama2:7b
   ```
   > Ollama is optional if you only use manual capability tags (skip `--auto-caps`). It is required for the client LLM simulation and auto-capability inference.

3. **Git** (for cloning and contributing)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/axiomeer.git
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
| `executor_type` | string | Executor protocol (v1 supports `http_api` only) |
| `executor_url` | string | HTTP endpoint the marketplace calls to execute this app |

### 2. Publish to the marketplace

```bash
python -m marketplace.cli publish manifests/realtime_weather_agent.json
```

Publishing is idempotent -- running it again updates the existing listing.

### 3. Verify the listing

```bash
python -m marketplace.cli apps
```

---

## Client LLM Simulation

The client LLM script demonstrates the full end-to-end pipeline: an LLM shops the marketplace, executes a tool, assesses evidence quality, and either answers with grounded citations or abstains.

```bash
python -m marketplace.client_llm "What is the weather in Indianapolis right now? Cite sources."
```

**Pipeline steps:**
1. Infer capabilities from the natural language question
2. Shop the marketplace with inferred constraints
3. Execute the top-ranked tool
4. Assess evidence quality (deterministic: HIGH / MEDIUM / LOW)
5. If **HIGH**: generate a grounded answer constrained to provided evidence
6. If **LOW**: abstain deterministically (no hallucination)

> Requires Ollama running with `llama2:7b` pulled.

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
| `GET` | `/providers/weather` | Mock weather provider (test data) |
| `GET` | `/providers/static-weather` | Mock static weather provider |
| `GET` | `/providers/openmeteo_weather` | Real Open-Meteo weather (free, no API key) |

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

The router scores apps using weighted criteria:

| Weight | Factor | Description |
|--------|--------|-------------|
| 70% | Capability Match | Coverage ratio of required vs. available capabilities |
| 20% | Latency | Penalizes high latency with a soft curve |
| 10% | Cost | Prefers cheaper without over-penalizing |

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
| `API_BASE_URL` | `http://127.0.0.1:8000` | API server URL (used by CLI and client) |
| `OLLAMA_URL` | `http://localhost:11434/api/generate` | Ollama inference endpoint |
| `OLLAMA_TIMEOUT` | `30` | Ollama request timeout in seconds |
| `ROUTER_MODEL` | `llama2:7b` | Model for capability extraction |
| `ANSWER_MODEL` | `llama2:7b` | Model for grounded answer generation |
| `W_CAP` | `0.70` | Router weight: capability match |
| `W_LAT` | `0.20` | Router weight: latency |
| `W_COST` | `0.10` | Router weight: cost |

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
│ realtime_weather_agent │ Realtime Weather Agent v2 │ realtime  │ yes       │ weather,realtime,citations │
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
Ranked apps by capability match (primary), then latency, then cost.
                       Top Recommendations
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ # ┃ app_id                 ┃ name                      ┃ score ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ 1 │ realtime_weather_agent │ Realtime Weather Agent v2 │ 0.877 │
└───┴────────────────────────┴───────────────────────────┴───────┘

Top pick: Realtime Weather Agent v2 (realtime_weather_agent)
 - Capability match: 1.00 (covers ['citations', 'realtime', 'weather'])
 - Freshness matches requirement: realtime
 - Supports citations/provenance: yes
 - Estimated latency: 800ms
 - Estimated cost: $0.0000
```

**What happened:** The LLM inferred `['realtime', 'weather', 'citations']` from the query. The router scored the weather agent at 0.877 (1.00 capability match, penalized slightly on latency).

### Step 5: Shop + Execute the top pick

Adding `--execute-top` calls the provider, validates the output, and logs a receipt.

```bash
$ python -m marketplace.cli shop \
    "I need current realtime weather data for Indianapolis with citations" \
    --auto-caps --freshness realtime --citations --execute-top

...
Execution result:
ok=True
Provenance:
{
    'sources': ['https://open-meteo.com/'],
    'retrieved_at': '2026-02-02T15:14:22.989416+00:00',
    'notes': []
}
Output:
{
    'answer': 'At 2026-02-02T15:00, temperature is -2.7 C, weather_code=3,
              wind_speed=15.3 km/h (Open-Meteo).',
    'citations': ['https://open-meteo.com/'],
    'retrieved_at': '2026-02-02T15:14:22.989416+00:00',
    'quality': 'verified'
}
```

**What happened:**
1. The marketplace called the Open-Meteo provider via `executor_url`
2. Output validation passed: `citations` is a non-empty list, `retrieved_at` is present
3. `ok=True` -- execution succeeded
4. A receipt was logged to the `runs` table

### Step 6: Check execution receipts

Every execution (success or failure) is logged with latency and timestamp.

```bash
$ python -m marketplace.cli runs --n 5

                              Recent Runs (top 5)
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ id ┃ app_id                 ┃ ok   ┃ latency_ms ┃ created_at                   ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│  9 │ realtime_weather_agent │ True │        604 │ 2026-02-02T15:14:22.974...   │
│  8 │ realtime_weather_agent │ True │        621 │ 2026-02-02T14:47:11.216...   │
└────┴────────────────────────┴──────┴────────────┴──────────────────────────────┘
```

### Step 7: Full client LLM simulation (end-to-end)

This runs the complete pipeline: LLM asks a question, shops the marketplace, executes a tool, assesses evidence quality, and generates a grounded answer (or abstains).

```bash
$ python -m marketplace.client_llm \
    "What is the weather in Indianapolis right now? Cite sources."
```

**Output:**

```
╭──────────────────────────── Client LLM ────────────────────────────╮
│ Question                                                           │
│ What is the weather in Indianapolis right now? Cite sources.       │
│                                                                    │
│ Inferred caps                                                      │
│ ['weather', 'realtime', 'citations', 'search']                     │
╰────────────────────────────────────────────────────────────────────╯
```

The LLM extracted capability tags from the natural language question.

```
╭──────────────────── Marketplace /shop response ────────────────────╮
│ {                                                                  │
│   "status": "OK",                                                  │
│   "recommendations": [                                             │
│     {                                                              │
│       "app_id": "realtime_weather_agent",                          │
│       "name": "Realtime Weather Agent v2",                         │
│       "score": 0.702,                                              │
│       "why": [                                                     │
│         "Capability match: 0.75 (covers ['citations', 'realtime', │
│          'weather'])",                                              │
│         "Missing: ['search']",                                     │
│         "Freshness matches requirement: realtime",                 │
│         "Supports citations/provenance: yes",                      │
│         "Estimated latency: 800ms"                                 │
│       ]                                                            │
│     }                                                              │
│   ],                                                               │
│   "explanation": [                                                 │
│     "Ranked apps by capability match (primary), then latency,     │
│      then cost."                                                   │
│   ]                                                                │
│ }                                                                  │
╰────────────────────────────────────────────────────────────────────╯
```

The router ranked the weather agent. Score is 0.702 (75% capability match -- covers weather/realtime/citations but not search).

```
╭────────────────── Marketplace /execute response ───────────────────╮
│ {                                                                  │
│   "app_id": "realtime_weather_agent",                              │
│   "ok": true,                                                      │
│   "output": {                                                      │
│     "answer": "At 2026-02-02T15:00, temperature is -2.7 C,        │
│       weather_code=3, wind_speed=15.3 km/h (Open-Meteo).",        │
│     "citations": ["https://open-meteo.com/"],                      │
│     "retrieved_at": "2026-02-02T15:14:46.460875+00:00",            │
│     "quality": "verified"                                          │
│   },                                                               │
│   "provenance": {                                                  │
│     "sources": ["https://open-meteo.com/"],                        │
│     "retrieved_at": "2026-02-02T15:14:46.460875+00:00",            │
│     "notes": []                                                    │
│   },                                                               │
│   "validation_errors": []                                          │
│ }                                                                  │
╰────────────────────────────────────────────────────────────────────╯
```

The provider returned real weather data. Validation passed (citations present, timestamp present).

```
╭──────────────────────── Evidence Quality ──────────────────────────╮
│ {                                                                  │
│   "quality": "HIGH",                                               │
│   "reasons": [                                                     │
│     "Evidence appears non-mock and contains citations."            │
│   ]                                                                │
│ }                                                                  │
╰────────────────────────────────────────────────────────────────────╯
```

Evidence quality is **HIGH** (non-mock, has citations). The LLM proceeds to generate an answer.

```
╭──────────────────── Final Answer (Grounded) ───────────────────────╮
│ According to the provided evidence, the weather in Indianapolis    │
│ right now is -2.7 degrees Celsius with a wind speed of 15.3 km/h. │
│ This information was retrieved from Open-Meteo on February 2nd,    │
│ 2026 at 15:14:46 UTC and has been verified. Therefore, the current │
│ weather in Indianapolis is cold and windy. (Open-Meteo, 2026)      │
╰────────────────────────────────────────────────────────────────────╯
```

The LLM answered using **only** the evidence provided, with proper citations. No hallucination.

### What happens with mock/low-quality evidence

If the provider returns mock data (e.g., the `/providers/weather` mock endpoint), the pipeline detects it and **abstains** instead of answering:

```
╭──────────────────────── Evidence Quality ──────────────────────────╮
│ {                                                                  │
│   "quality": "LOW",                                                │
│   "reasons": ["Provider marked quality=mock."]                     │
│ }                                                                  │
╰────────────────────────────────────────────────────────────────────╯
╭──────────────────── Final Answer (Abstain) ────────────────────────╮
│ I don't have reliable evidence to answer this accurately.          │
│ Here is the evidence returned (may be mock/test) and its           │
│ citation(s).                                                       │
╰────────────────────────────────────────────────────────────────────╯
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
| 2 | `router` | Rank apps by capability (70%), latency (20%), cost (10%) with hard filters | NO_MATCH if nothing passes filters |
| 3 | Execute | Call provider's `executor_url`, get JSON response | Fail if provider unreachable |
| 4 | `validate` | Check citations list and `retrieved_at` timestamp | `ok=false` if validation fails |
| 5 | `evidence_quality` | Deterministic check: is data mock/simulated/fake? | -- |
| 6 | Answer/Abstain | If HIGH: LLM generates grounded answer. If LOW: abstain. | Prevents hallucination |
| 7 | `runs` table | Log receipt (app_id, task, ok, latency, errors, timestamp) | Always logged |

---

## Roadmap

- [x] ~~Add test suite (pytest)~~
- [x] ~~Move configuration to environment variables / `.env` file~~
- [ ] Add more apps: local search index, docs summarizer, finance, math, code execution sandbox
- [ ] Add manifest validation (JSON schema + allowlist enforcement)
- [ ] Add trust scores per provider (failure rate, citation compliance)
- [ ] Add multi-tool plans (LLM chains tool #1 into tool #2)
- [ ] Add ingestion bundles (structured chunks/snippets for downstream LLMs)
- [ ] Add authentication and API key support
- [ ] Add Docker containerization

---

## Contributing

Contributions are welcome. Here is how to get started:

### 1. Fork and clone

```bash
git clone https://github.com/<your-username>/axiomeer.git
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

All 67 tests should pass before making any changes.

### 4. Start the API server

```bash
uvicorn apps.api.main:app --reload
```

### 5. Publish the example app and verify

```bash
python -m marketplace.cli publish manifests/realtime_weather_agent.json
python -m marketplace.cli apps
python -m marketplace.cli shop "weather" --auto-caps --execute-top
python -m marketplace.cli runs
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
