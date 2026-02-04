import json
from typing import Any

from marketplace.llm.ollama_client import ollama_generate, OllamaConnectionError
from marketplace.settings import ROUTER_MODEL


class SalesAgentError(RuntimeError):
    """Raised when the sales agent cannot produce a valid recommendation."""


PROMPT = """You are a marketplace sales agent. Your job is to recommend the single best product for the client.

Given:
- The client task
- The marketplace constraints
- A list of candidate products with metadata and scores

Return ONLY valid JSON in this schema:
{{
  "app_id": "string",
  "rationale": "string"
}}

Rules:
- Choose exactly one app_id from the candidates list.
- If none are suitable, return app_id "NO_MATCH" and explain why.
- Prefer NO_MATCH if the task asks for specific facts that the candidates are unlikely to provide (e.g., fictional entities or data not covered by any candidate capabilities).
- Use candidate capabilities as the primary signal for domain fit. If the task is about finance and no candidate has a finance capability, return NO_MATCH.
- Prefer candidates whose capabilities overlap with REQUESTED_CAPABILITIES. If REQUESTED_CAPABILITIES includes finance, choose a finance-capable candidate when available.
- The rationale must be grounded in the provided candidate data.
- Do not mention other apps unless comparing them directly.
- Do not include any extra keys or text.

TASK:
{task}

CONSTRAINTS:
{constraints_json}

REQUESTED_CAPABILITIES:
{requested_caps_json}

RECENT_HISTORY:
{history_json}

CANDIDATES:
{candidates_json}
"""

NO_MATCH_PROMPT = """You are a marketplace sales agent. There are no suitable products for the client request.

Given:
- The client task
- The marketplace constraints
- The fact that no candidates matched

Return ONLY valid JSON in this schema:
{{
  "message": "string"
}}

Rules:
- Do not invent products or data sources.
- Explain briefly why no suitable product exists.
- Suggest what could be relaxed or added to find a match.

TASK:
{task}

CONSTRAINTS:
{constraints_json}

RECENT_HISTORY:
{history_json}
"""


def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if "{" in raw and "}" in raw:
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    return raw


def sales_recommendation(
    task: str,
    constraints: dict[str, Any],
    candidates: list[dict[str, Any]],
    requested_caps: list[str] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    try:
        raw = ollama_generate(
            ROUTER_MODEL,
            PROMPT.format(
                task=task,
                constraints_json=json.dumps(constraints, ensure_ascii=True),
                requested_caps_json=json.dumps(requested_caps or [], ensure_ascii=True),
                history_json=json.dumps(history or [], ensure_ascii=True),
                candidates_json=json.dumps(candidates, ensure_ascii=True),
            ),
        )
    except OllamaConnectionError as e:
        raise SalesAgentError(str(e)) from e

    payload = json.loads(_extract_json(raw))
    app_id = payload.get("app_id")
    rationale = payload.get("rationale")

    if not isinstance(app_id, str) or not app_id.strip():
        raise SalesAgentError("sales_agent_invalid_app_id")
    if not isinstance(rationale, str) or not rationale.strip():
        raise SalesAgentError("sales_agent_invalid_rationale")

    if app_id != "NO_MATCH":
        valid_ids = {c.get("app_id") for c in candidates}
        if app_id not in valid_ids:
            raise SalesAgentError("sales_agent_app_id_not_in_candidates")

    return {"app_id": app_id, "rationale": rationale.strip()}


def sales_no_match(
    task: str,
    constraints: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    try:
        raw = ollama_generate(
            ROUTER_MODEL,
            NO_MATCH_PROMPT.format(
                task=task,
                constraints_json=json.dumps(constraints, ensure_ascii=True),
                history_json=json.dumps(history or [], ensure_ascii=True),
            ),
        )
    except OllamaConnectionError as e:
        raise SalesAgentError(str(e)) from e

    payload = json.loads(_extract_json(raw))
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise SalesAgentError("sales_agent_invalid_no_match_message")
    return {"message": message.strip()}
