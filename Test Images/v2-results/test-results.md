# Axiomeer v3 -- End-to-End Test Results

Tested on: 2026-02-04
Model: qwen2.5:14b-instruct (local via Ollama)
All 7 providers auto-loaded, tests run against live external APIs where available.

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
