import json
from marketplace.llm.ollama_client import ollama_generate, OllamaConnectionError
from marketplace.settings import ROUTER_MODEL

ALLOWED_CAPS = {"weather", "finance", "search", "realtime", "citations", "math", "coding", "docs", "summarize", "translate"}

DOMAIN_KEYWORDS = {
    "weather": ["weather", "temperature", "forecast", "rain", "snow", "humidity", "wind", "storm", "climate"],
    "finance": ["cpi", "inflation", "stock", "market", "price", "gdp", "unemployment", "earnings", "revenue", "interest rate", "exchange rate", "currency", "forex", "dollar", "euro", "yen"],
    "math": ["calculate", "compute", "solve", "equation", "derivative", "integral", "number", "prime", "factorial"],
    "coding": ["python", "javascript", "bug", "error", "stack trace", "compile", "code", "function"],
    "translate": ["translate", "translation", "in spanish", "in french", "in hindi"],
    "summarize": ["summarize", "summary", "tl;dr", "key points"],
    "docs": ["documentation", "api docs", "readme", "spec", "schema", "definition", "meaning", "dictionary", "define"],
    "search": ["search", "look up", "find", "who is", "what is", "where is", "country", "capital", "population", "book", "author", "library"],
}

# Braces escaped because we use .format()
PROMPT = """You extract capability tags for Axiomeer, the marketplace for AI agents.

Return ONLY valid JSON with this schema:
{{
  "capabilities": ["tag1","tag2",...]
}}

Rules:
- Use lowercase tags.
- Only output tags from this allowed list:
  ["weather","finance","search","realtime","citations","math","coding","docs","summarize","translate"]
- If the request implies "latest/current/now/today", include "realtime".
- If it asks for sources/citations/links, include "citations".
- If unclear, return {{"capabilities": []}}.

Request:
{task}
"""


def _heuristic_caps(task: str, force_citations: bool) -> list[str]:
    """Deterministic keyword-based capability extraction."""
    t = task.lower()
    caps: list[str] = []
    seen: set[str] = set()

    for cap, words in DOMAIN_KEYWORDS.items():
        if any(w in t for w in words) and cap not in seen:
            seen.add(cap)
            caps.append(cap)

    if force_citations or any(w in t for w in ["citation", "citations", "cite", "sources", "source", "link", "links"]):
        if "citations" not in seen:
            seen.add("citations")
            caps.append("citations")

    if any(w in t for w in ["latest", "current", "today", "now", "this week"]):
        if "realtime" not in seen:
            caps.append("realtime")

    return caps


def extract_capabilities(task: str, force_citations: bool = False) -> list[str]:
    # Try LLM extraction first, fall back to heuristics on failure
    try:
        raw = ollama_generate(ROUTER_MODEL, PROMPT.format(task=task))
    except OllamaConnectionError:
        return _heuristic_caps(task, force_citations)

    raw = raw.strip()
    if "{" in raw and "}" in raw:
        raw = raw[raw.find("{") : raw.rfind("}") + 1]

    try:
        obj = json.loads(raw)
        caps = obj.get("capabilities", [])
        if not isinstance(caps, list):
            return _heuristic_caps(task, force_citations)

        # Dedupe + filter to allowed set
        seen: set[str] = set()
        deduped: list[str] = []
        for c in caps:
            if isinstance(c, str) and c.strip():
                c = c.strip().lower()
                if c in ALLOWED_CAPS and c not in seen:
                    seen.add(c)
                    deduped.append(c)

        # Augment with heuristics
        t = task.lower()
        for cap, words in DOMAIN_KEYWORDS.items():
            if any(w in t for w in words) and cap not in seen:
                seen.add(cap)
                deduped.append(cap)

        if force_citations or any(w in t for w in ["citation", "citations", "cite", "sources", "source", "link", "links"]):
            if "citations" not in seen:
                seen.add("citations")
                deduped.append("citations")

        if any(w in t for w in ["latest", "current", "today", "now", "this week"]):
            if "realtime" not in seen:
                deduped.append("realtime")

        return deduped

    except Exception:
        return _heuristic_caps(task, force_citations)
