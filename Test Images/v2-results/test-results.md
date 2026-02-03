# Axiomeer v2 -- End-to-End Test Results

Tested on: 2026-02-03
Model: llama2:7b (local via Ollama)
All 7 providers auto-loaded, all tests run against live external APIs.

---

## Test 1: Real Query -- Weather in Indianapolis

**Query:** "What is the weather in Indianapolis right now? Cite sources."

### Step 1: Capability Extraction
```
Inferred caps: ['weather', 'citations', 'search', 'realtime']
```

### Step 2: Shop (Router)
```json
{
  "status": "OK",
  "recommendations": [
    {
      "app_id": "realtime_weather_agent",
      "name": "Realtime Weather Agent v2",
      "score": 0.702,
      "why": [
        "Capability match: 0.75 (covers ['citations', 'realtime', 'weather'])",
        "Freshness matches requirement: realtime",
        "Supports citations/provenance: yes",
        "Estimated latency: 800ms"
      ]
    }
  ]
}
```
Router correctly selected the weather provider as the top pick.

### Step 3: Execute
```json
{
  "app_id": "realtime_weather_agent",
  "ok": true,
  "output": {
    "answer": "At 2026-02-03T21:45, temperature is 0.0 C, weather_code=0, wind_speed=10.4 km/h (Open-Meteo).",
    "citations": ["https://open-meteo.com/"],
    "retrieved_at": "2026-02-03T21:49:00.630211+00:00",
    "quality": "verified"
  },
  "provenance": {
    "sources": ["https://open-meteo.com/"],
    "retrieved_at": "2026-02-03T21:49:00.630211+00:00"
  },
  "validation_errors": []
}
```
Real data from Open-Meteo. Citation present. Validation passed.

### Step 4: Evidence Quality
```json
{
  "quality": "HIGH",
  "reasons": ["Evidence appears non-mock and contains citations."]
}
```

### Step 5: Final Grounded Answer
```
According to the available evidence, the temperature in Indianapolis at
2026-02-03T21:45 is 0.0 C. The wind speed is 10.4 km/h. This information
was obtained from Open-Meteo, a reliable weather data source.
```

**Result: PASS** -- Real data, correct routing, grounded answer, no hallucination.

---

## Test 2: Fake Query -- GDP of Wakanda

**Query:** "What is the GDP of Wakanda in 2025? Cite sources."

### Step 1: Capability Extraction
```
Inferred caps: ['realtime', 'citations', 'finance', 'search']
```

### Step 2: Shop (Router)
```json
{
  "status": "OK",
  "recommendations": [
    {
      "app_id": "exchange_rates",
      "name": "Exchange Rate Lookup",
      "score": 0.725,
      "why": [
        "Capability match: 0.75 (covers ['citations', 'finance', 'realtime'])",
        "Freshness matches requirement: realtime",
        "Supports citations/provenance: yes"
      ]
    }
  ]
}
```
Router picked the closest match (finance + realtime). No GDP provider exists.

### Step 3: Execute
```json
{
  "app_id": "exchange_rates",
  "ok": true,
  "output": {
    "answer": "Exchange rates for 1 USD: EUR: 0.846294, GBP: 0.731608, JPY: 155.348973, CAD: 1.367158, AUD: 1.438541, CHF: 0.778587.",
    "citations": ["https://open.er-api.com/v6/latest/USD"],
    "quality": "verified"
  },
  "validation_errors": []
}
```
Provider returned real exchange rate data (which is valid data, but irrelevant to the question).

### Step 4: Evidence Quality
```json
{
  "quality": "HIGH",
  "reasons": ["Evidence appears non-mock and contains citations."]
}
```
Evidence quality is HIGH (real data with citations). The quality check verifies data authenticity, not relevance.

### Step 5: Final Grounded Answer
```
The available evidence does not provide the GDP of Wakanda in 2025. The
sources provided are exchange rates for various currencies, but do not
include any information on the economic data or GDP of Wakanda. As such,
I cannot provide an answer to the question.
```

**Result: PASS** -- The LLM recognized the evidence does not answer the question and refused to hallucinate.

---

## Test 3: Direct Provider Tests (via /execute API)

| # | Provider | Query | Result | ok? | Hallucination? |
|---|----------|-------|--------|-----|----------------|
| 1 | Open-Meteo | NYC weather (lat=40.71, lon=-74.00) | -0.8 C, wind 4.5 km/h | true | No |
| 2 | REST Countries | Japan | Capital: Tokyo, Pop: 123.2M, Language: Japanese | true | No |
| 3 | Exchange Rates | EUR base | 1 EUR = 0.864 GBP, 183.5 JPY, 1.61 CAD | true | No |
| 4 | Dictionary | "algorithm" | "A collection of ordered steps that solve a mathematical problem" | true | No |
| 5 | Open Library | "machine learning" | "Why Machines Learn" (2024), "Machine learning" by Murphy (2012) | true | No |
| 6 | Wikipedia | Albert Einstein | Born German, theory of relativity, E=mc2, Nobel 1921 | true | No |

---

## Test 4: Failure Cases (No Hallucination)

| # | Provider | Query | Response | ok? | Hallucination? |
|---|----------|-------|----------|-----|----------------|
| 1 | REST Countries | "Wakanda" | "No country found matching 'Wakanda'." | false | No |
| 2 | Dictionary | "xyzblurgh" | "No definition found for 'xyzblurgh'." | false | No |
| 3 | Wikipedia | "Flurbnozzle_xyznonexistent" | "No Wikipedia article found for 'Flurbnozzle...'" | false | No |
| 4 | (unknown app) | "totally_fake_app" | "Unknown app_id" | false | No |

All failure cases:
- Returned structured error responses (not crashes)
- Empty citations triggered validation failure (ok=false)
- No invented or hallucinated data

---

## Summary

| Metric | Result |
|--------|--------|
| Total providers tested | 7 |
| Real data accuracy | 6/6 correct |
| Fake data handling | 4/4 correctly refused |
| LLM hallucination | 0 instances |
| End-to-end pipeline | Working (shop -> route -> execute -> validate -> ground) |
| Unit tests | 83/83 pass |
| Integration tests | 9/9 pass |
