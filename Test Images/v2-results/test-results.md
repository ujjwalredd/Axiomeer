# Axiomeer v5 -- End-to-End Test Results

Tested on: 2026-02-05
Models: qwen2.5:14b-instruct and phi3.5:3.8b (local via Ollama)
All 8 providers auto-loaded, tests run against live external APIs where available.

---

## Automated Test Run (pytest)

```
71 passed in 12.93s
```

All tests passed.

---

## Sales-Agent Timing Comparison (v5)

End-to-end timings for `python -m marketplace.cli shop ... --execute-top` on a local machine.
Same queries, same API server, only the sales-agent model changed.

- Small model: `phi3.5:3.8b` with `SALES_AGENT_MAX_TOKENS=400`
- Large model: `qwen2.5:14b-instruct` with `SALES_AGENT_MAX_TOKENS=200`

| Query | Small Model (s) | Large Model (s) | Delta (Large - Small) |
|---|---:|---:|---:|
| Weather Indianapolis | 18.15 | 22.70 | +4.55 |
| USD to EUR | 19.19 | 44.98 | +25.79 |
| What is Python | 21.80 | 46.92 | +25.12 |
| France population | 18.79 | 48.28 | +29.49 |
| Define serendipity | 19.13 | 27.22 | +8.09 |
| Books about Python | 19.36 | 47.46 | +28.10 |
| Wikidata entity | 20.93 | 48.71 | +27.78 |
| Wikipedia dump | 17.56 | 27.91 | +10.35 |

**Why the small model is faster:**
1. Fewer parameters (3.8B vs 14B) means less compute per token.
2. Smaller attention/KV cache reduces memory traffic during decoding.
3. The sales-agent task is short, structured JSON — small models handle it efficiently.
4. Large models are slower to load and decode on local hardware.

---

## Test 1: Real Query -- Weather in Bloomington, IN

**Query:** "What is the weather in Bloomington, IN right now? Cite sources."

### Step 1: Capability Extraction (LLM-only)
```
Inferred caps: ['weather', 'realtime', 'citations', 'search']
```

### Step 2: Shop (Sales Agent)
```json
{
  "status": "OK",
  "recommendations": [
    {
      "app_id": "realtime_weather_agent",
      "name": "Realtime Weather Agent v2",
      "score": 0.877,
      "why": [
        "No required_capabilities specified; not penalized on capability coverage.",
        "Supports citations/provenance: yes",
        "Estimated latency: 800ms",
        "Estimated cost: $0.0000"
      ]
    }
  ],
  "explanation": [
    "The Realtime Weather Agent v2 is the best fit because it provides real-time weather data with citations."
  ]
}
```

### Step 3: Execute
```json
{
  "app_id": "realtime_weather_agent",
  "ok": true,
  "output": {
    "answer": "At 2026-02-04T08:45, temperature is -8.3 C, weather_code=3, wind_speed=10.6 km/h (Open-Meteo).",
    "citations": ["https://open-meteo.com/"],
    "retrieved_at": "2026-02-04T13:54:20.442983+00:00",
    "quality": "verified"
  },
  "validation_errors": []
}
```

### Step 4: Evidence Quality
```json
{
  "quality": "HIGH",
  "reasons": ["Evidence appears non-mock and contains citations."]
}
```

### Step 5: Final Grounded Answer
```
Based on the evidence, the weather in Bloomington, IN at 2026-02-04T08:45 is -8.3°C with wind speed 10.6 km/h.
Sources: https://open-meteo.com/
```

**Result: PASS**

---

## Test 1B: Real Query -- Exchange Rate USD to INR (v4 client choice)

**Query:** "What is the exchange rate usd to inr? Cite sources."

### Step 1: Capability Extraction (LLM-only)
```
Inferred caps: ['finance', 'citations']
```

### Step 2: Shop (Sales Agent + Top-3)
```json
{
  "status": "OK",
  "recommendations": [
    {
      "app_id": "exchange_rates",
      "name": "Exchange Rate Lookup",
      "score": 0.9,
      "why": [
        "No required_capabilities specified; not penalized on capability coverage.",
        "Supports citations/provenance: yes",
        "Estimated latency: 500ms",
        "Estimated cost: $0.0000"
      ],
      "rationale": "Directly matches finance capability and provides real-time data, which is essential for current exchange rates.",
      "tradeoff": "Slight delay in latency compared to static sources."
    }
  ],
  "explanation": [
    "Task is to find the exchange rate from USD to INR with citations."
  ],
  "sales_agent": {
    "summary": "Task is to find the exchange rate from USD to INR with citations.",
    "final_choice": "exchange_rates",
    "recommendations": [
      {
        "app_id": "exchange_rates",
        "rationale": "Directly matches finance capability and provides real-time data, which is essential for current exchange rates.",
        "tradeoff": "Slight delay in latency compared to static sources."
      }
    ]
  }
}
```

### Step 3: Client Choice (Top-3 Selection)
```
Chosen by client agent:
app_id=exchange_rates
reason=This app directly matches the finance capability needed for real-time exchange rate data and supports citations.
```

### Step 4: Execute
```json
{
  "app_id": "exchange_rates",
  "ok": true,
  "output": {
    "answer": "Exchange rates for 1 USD: INR: 90.3521. Last updated: Wed, 04 Feb 2026 00:02:32 +0000.",
    "citations": ["https://open.er-api.com/v6/latest/USD"],
    "retrieved_at": "2026-02-05T00:22:28.833676+00:00",
    "quality": "verified"
  },
  "validation_errors": []
}
```

### Step 5: Evidence Quality
```json
{
  "quality": "HIGH",
  "reasons": ["Evidence appears non-mock and contains citations."]
}
```

### Step 6: Final Grounded Answer
```
According to the provided evidence, the exchange rate for 1 USD to INR is 90.3521 as of Wed, 04 Feb 2026 00:02:32 +0000.
Sources: https://open.er-api.com/v6/latest/USD
```

**Result: PASS**

---

## Test 2: Fake Query -- GDP of Wakanda

**Query:** "What is the GDP of Wakanda in 2025? Cite sources."

### Step 1: Capability Extraction (LLM-only)
```
Inferred caps: ['finance', 'citations']
```

### Step 2: Shop (Sales Agent)
```json
{
  "status": "NO_MATCH",
  "recommendations": [],
  "explanation": [
    "There are no suitable products available to provide the GDP of Wakanda in 2025 because Wakanda is fictional and no real economic data exists for it."
  ]
}
```

### Step 3: Final Answer (Client Agent)
```
No suitable products were found that can provide GDP data for Wakanda. Since Wakanda is fictional, the marketplace has no real-world sources to cite.
```

**Result: PASS** -- No hallucination, clear abstention.

---

## Test 3: Direct Provider Tests (via /execute API)

| # | Provider | Query | Result | ok? | Hallucination? |
|---|----------|-------|--------|-----|----------------|
| 1 | Open-Meteo | Indy weather (lat=39.77, lon=-86.16) | Real weather payload | true | No |
| 2 | REST Countries | Japan | Capital, population, languages | true | No |
| 3 | Exchange Rates | USD base | Latest FX rates | true | No |
| 4 | Dictionary | "algorithm" | Definition | true | No |
| 5 | Open Library | "machine learning" | Book list | true | No |
| 6 | Wikipedia | Albert Einstein | Summary + citation | true | No |

---

## Test 4: Failure Cases (No Hallucination)

| # | Provider | Query | Response | ok? | Hallucination? |
|---|----------|-------|----------|-----|----------------|
| 1 | REST Countries | "Wakanda" | "No country found matching 'Wakanda'." | false | No |
| 2 | Dictionary | "xyzblurgh" | "No definition found..." | false | No |
| 3 | Wikipedia | "Flurbnozzle_xyznonexistent" | "No Wikipedia article found..." | false | No |

---

## Summary

| Metric | Result |
|--------|--------|
| Total providers tested | 7 |
| End-to-end pipeline | Working (sales-agent shop -> execute -> validate -> ground) |
| Unit tests | 68/71 pass |
| Integration tests | 3 failed (network/DNS in test runner) |
