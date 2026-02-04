import json
from marketplace.llm.ollama_client import ollama_generate, OllamaConnectionError
from marketplace.settings import ROUTER_MODEL

ALLOWED_CAPS = {"weather", "finance", "search", "realtime", "citations", "math", "coding", "docs", "summarize", "translate"}

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


def extract_capabilities(task: str, force_citations: bool = False) -> list[str]:
    # LLM-only capability extraction
    try:
        raw = ollama_generate(ROUTER_MODEL, PROMPT.format(task=task))
    except OllamaConnectionError:
        return []

    raw = raw.strip()
    if "{" in raw and "}" in raw:
        raw = raw[raw.find("{") : raw.rfind("}") + 1]

    try:
        obj = json.loads(raw)
        caps = obj.get("capabilities", [])
        if not isinstance(caps, list):
            return []

        # Dedupe + filter to allowed set
        seen: set[str] = set()
        deduped: list[str] = []
        for c in caps:
            if isinstance(c, str) and c.strip():
                c = c.strip().lower()
                if c in ALLOWED_CAPS and c not in seen:
                    seen.add(c)
                    deduped.append(c)

        return deduped

    except Exception:
        return []
