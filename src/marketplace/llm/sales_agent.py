import ast
import json
import re
from typing import Any

from marketplace.llm.ollama_client import ollama_generate, OllamaConnectionError
from marketplace.settings import (
    SALES_AGENT_MODEL,
    SALES_AGENT_MAX_TOKENS,
    SALES_AGENT_TEMPERATURE,
    SALES_AGENT_TIMEOUT,
)


class SalesAgentError(RuntimeError):
    """Raised when the sales agent cannot produce a valid recommendation."""


PROMPT = """You are a marketplace sales agent. Your job is to recommend the top 3 products for the client.

Given:
- The client task
- The marketplace constraints
- A list of candidate products with metadata and scores

Return ONLY valid JSON in this schema:
{{
  "summary": "string",
  "final_choice": "string",
  "recommendations": [
    {{
      "app_id": "string",
      "rationale": "string",
      "tradeoff": "string"
    }}
  ]
}}

Rules:
- Choose up to 3 app_ids from the candidates list, ordered best to worst.
- The final_choice must be one of the recommended app_ids.
- Use ONLY the strings in ALLOWED_APP_IDS for final_choice and recommendation app_id values.
- If none are suitable, set final_choice to "NO_MATCH", return an empty recommendations list, and explain why in summary.
- Prefer NO_MATCH if the task asks for specific facts that the candidates are unlikely to provide (e.g., fictional entities or data not covered by any candidate capabilities).
- Use candidate capabilities as the primary signal for domain fit. If the task is about finance and no candidate has a finance capability, return NO_MATCH.
- Prefer candidates whose capabilities overlap with REQUESTED_CAPABILITIES. If REQUESTED_CAPABILITIES includes finance, choose a finance-capable candidate when available.
- The rationale and tradeoff must be grounded in the provided candidate data.
- Keep summary concise and grounded in the candidate list.
- Do not include any extra keys or text.

TASK:
{task}

CONSTRAINTS:
{constraints_json}

REQUESTED_CAPABILITIES:
{requested_caps_json}

ALLOWED_APP_IDS:
{allowed_ids_json}

RECENT_HISTORY:
{history_json}

CANDIDATES:
{candidates_json}
"""

STRICT_PROMPT = """Return ONLY valid JSON for the schema below. No extra text, no markdown, no code fences.

SCHEMA:
{{
  "summary": "string",
  "final_choice": "string",
  "recommendations": [
    {{
      "app_id": "string",
      "rationale": "string",
      "tradeoff": "string"
    }}
  ]
}}

TASK:
{task}

CONSTRAINTS:
{constraints_json}

REQUESTED_CAPABILITIES:
{requested_caps_json}

ALLOWED_APP_IDS:
{allowed_ids_json}

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

REPAIR_JSON_PROMPT = """You are a JSON repair tool. Fix the input to valid JSON that matches the required schema exactly.
Rules:
- Preserve the original meaning.
- Do not add new fields or commentary.
- Return ONLY valid JSON.

REQUIRED_SCHEMA:
{schema_json}

INPUT:
{raw}
"""

REPAIR_SALES_PROMPT = """You are a JSON repair tool for a marketplace sales agent.
Fix the JSON to match the required schema AND the allowed app_ids.

Rules:
- Return ONLY valid JSON.
- final_choice MUST be one of ALLOWED_APP_IDS.
- recommendations MUST be a list (max 3) of objects with app_id from ALLOWED_APP_IDS.
- final_choice MUST be included in recommendations.
- Preserve the original meaning where possible.

TASK:
{task}

ALLOWED_APP_IDS:
{allowed_ids_json}

CANDIDATES:
{candidates_json}

REQUIRED_SCHEMA:
{schema_json}

INPUT:
{raw}
"""

def _extract_json(raw: str) -> str:
    raw = raw.strip()
    if "{" in raw and "}" in raw:
        raw = raw[raw.find("{") : raw.rfind("}") + 1]
    return raw

def _safe_json_load(raw: str) -> dict[str, Any] | None:
    cleaned = _extract_json(raw)
    if not cleaned:
        return None
    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass
    cleaned = re.sub(r",\s*([}\]])", r"\1", cleaned)
    try:
        payload = json.loads(cleaned)
        return payload if isinstance(payload, dict) else None
    except json.JSONDecodeError:
        pass
    try:
        payload = ast.literal_eval(cleaned)
        return payload if isinstance(payload, dict) else None
    except Exception:
        return None

def _repair_json(raw: str, schema: dict[str, Any]) -> dict[str, Any]:
    fixed = ollama_generate(
        SALES_AGENT_MODEL,
        REPAIR_JSON_PROMPT.format(
            schema_json=json.dumps(schema, ensure_ascii=True),
            raw=raw,
        ),
        options={
            "temperature": 0.0,
            "num_predict": SALES_AGENT_MAX_TOKENS,
        },
        response_format=None,
        timeout=SALES_AGENT_TIMEOUT,
    )
    payload = _safe_json_load(fixed)
    if payload is None:
        raise ValueError("repair_json_invalid")
    return payload

def _repair_sales_payload(
    raw: str,
    task: str,
    candidates: list[dict[str, Any]],
    allowed_ids: list[str],
) -> dict[str, Any]:
    fixed = ollama_generate(
        SALES_AGENT_MODEL,
        REPAIR_SALES_PROMPT.format(
            task=task,
            allowed_ids_json=json.dumps(allowed_ids, ensure_ascii=True),
            candidates_json=json.dumps(candidates, ensure_ascii=True),
            schema_json=json.dumps(
                {
                    "summary": "string",
                    "final_choice": "string",
                    "recommendations": [
                        {"app_id": "string", "rationale": "string", "tradeoff": "string"}
                    ],
                },
                ensure_ascii=True,
            ),
            raw=raw,
        ),
        options={
            "temperature": 0.0,
            "num_predict": SALES_AGENT_MAX_TOKENS,
        },
        response_format=None,
        timeout=SALES_AGENT_TIMEOUT,
    )
    payload = _safe_json_load(fixed)
    if payload is None:
        raise ValueError("repair_sales_invalid")
    return payload

def _parse_sales_payload(
    payload: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    def _normalize_label(value: str) -> str:
        return re.sub(r"[^a-z0-9]+", "", value.lower())

    def _coerce_choice(value: Any) -> Any:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            for key in ("app_id", "id", "name"):
                if key in value:
                    return _coerce_choice(value.get(key))
            if len(value) == 1:
                return _coerce_choice(next(iter(value.values())))
            return None
        if isinstance(value, list):
            if len(value) == 1:
                return _coerce_choice(value[0])
            return None
        return value

    def _resolve_app_id(
        value: Any,
        valid_ids: set[str],
        name_map: dict[str, str],
    ) -> str | None:
        if not isinstance(value, str):
            return None
        candidate = value.strip()
        if not candidate:
            return None
        if candidate in valid_ids:
            return candidate
        lowered = candidate.lower()
        if lowered in valid_ids:
            return lowered
        matches = [vid for vid in valid_ids if vid in lowered]
        if len(matches) == 1:
            return matches[0]
        norm = _normalize_label(candidate)
        return name_map.get(norm)

    summary = payload.get("summary")
    final_choice = _coerce_choice(payload.get("final_choice"))
    recommendations = payload.get("recommendations")

    if not isinstance(summary, str) or not summary.strip():
        raise SalesAgentError("sales_agent_invalid_summary")
    if not isinstance(final_choice, str) or not final_choice.strip():
        final_choice = None
    if not isinstance(recommendations, list):
        raise SalesAgentError("sales_agent_invalid_recommendations")

    candidate_map: dict[str, dict[str, Any]] = {
        c.get("app_id"): c for c in candidates if c.get("app_id")
    }

    valid_ids = {c.get("app_id") for c in candidates if c.get("app_id")}
    name_map: dict[str, str] = {}
    collisions: set[str] = set()
    for c in candidates:
        name = c.get("name")
        app_id = c.get("app_id")
        if not isinstance(name, str) or not isinstance(app_id, str):
            continue
        key = _normalize_label(name)
        if not key:
            continue
        if key in name_map and name_map[key] != app_id:
            collisions.add(key)
        else:
            name_map[key] = app_id
    for key in collisions:
        name_map.pop(key, None)

    if final_choice == "NO_MATCH":
        if recommendations:
            raise SalesAgentError("sales_agent_no_match_with_recommendations")
        return {
            "summary": summary.strip(),
            "final_choice": "NO_MATCH",
            "recommendations": [],
        }

    if not recommendations:
        raise SalesAgentError("sales_agent_missing_recommendations")
    if len(recommendations) > 3:
        raise SalesAgentError("sales_agent_too_many_recommendations")

    resolved_final = _resolve_app_id(final_choice, valid_ids, name_map)

    seen = set()
    parsed_recs: list[dict[str, str]] = []
    for rec in recommendations:
        if not isinstance(rec, dict):
            raise SalesAgentError("sales_agent_invalid_recommendation_entry")
        app_id = _coerce_choice(rec.get("app_id"))
        rationale = rec.get("rationale")
        tradeoff = rec.get("tradeoff")
        resolved_app_id = _resolve_app_id(app_id, valid_ids, name_map)
        if resolved_app_id is None:
            raise SalesAgentError("sales_agent_invalid_app_id")
        if resolved_app_id in seen:
            raise SalesAgentError("sales_agent_duplicate_app_id")
        if not isinstance(rationale, str) or not rationale.strip():
            candidate = candidate_map.get(resolved_app_id, {})
            rationale_bits: list[str] = []
            caps = candidate.get("capabilities") or []
            if caps:
                rationale_bits.append(f"Capabilities: {', '.join(caps)}")
            freshness = candidate.get("freshness")
            if freshness:
                rationale_bits.append(f"Freshness: {freshness}")
            if candidate.get("citations_supported"):
                rationale_bits.append("Supports citations")
            rationale = "; ".join(rationale_bits) if rationale_bits else None
        if not isinstance(rationale, str) or not rationale.strip():
            raise SalesAgentError("sales_agent_invalid_rationale")
        if not isinstance(tradeoff, str) or not tradeoff.strip():
            candidate = candidate_map.get(resolved_app_id, {})
            tradeoff_bits: list[str] = []
            latency = candidate.get("latency_est_ms")
            if latency is not None:
                tradeoff_bits.append(f"Estimated latency: {latency}ms")
            cost = candidate.get("cost_est_usd")
            if cost is not None:
                tradeoff_bits.append(f"Estimated cost: ${float(cost):.4f}")
            tradeoff = "; ".join(tradeoff_bits) if tradeoff_bits else None
        if not isinstance(tradeoff, str) or not tradeoff.strip():
            raise SalesAgentError("sales_agent_invalid_tradeoff")
        seen.add(resolved_app_id)
        parsed_recs.append({
            "app_id": resolved_app_id,
            "rationale": rationale.strip(),
            "tradeoff": tradeoff.strip(),
        })

    if not parsed_recs:
        raise SalesAgentError("sales_agent_missing_recommendations")

    if resolved_final is None or resolved_final not in seen:
        resolved_final = parsed_recs[0]["app_id"]

    return {
        "summary": summary.strip(),
        "final_choice": resolved_final,
        "recommendations": parsed_recs,
    }


def _generate_sales_json(
    task: str,
    constraints: dict[str, Any],
    candidates: list[dict[str, Any]],
    requested_caps: list[str] | None,
    history: list[dict[str, Any]] | None,
    strict: bool,
    response_format: str | None,
) -> str:
    prompt = PROMPT if not strict else STRICT_PROMPT
    allowed_ids = [c.get("app_id") for c in candidates if c.get("app_id")]
    return ollama_generate(
        SALES_AGENT_MODEL,
        prompt.format(
            task=task,
            constraints_json=json.dumps(constraints, ensure_ascii=True),
            requested_caps_json=json.dumps(requested_caps or [], ensure_ascii=True),
            allowed_ids_json=json.dumps(allowed_ids, ensure_ascii=True),
            history_json=json.dumps(history or [], ensure_ascii=True),
            candidates_json=json.dumps(candidates, ensure_ascii=True),
        ),
        options={
            "temperature": SALES_AGENT_TEMPERATURE,
            "num_predict": SALES_AGENT_MAX_TOKENS,
        },
        response_format=response_format,
        timeout=SALES_AGENT_TIMEOUT,
    )


def sales_recommendation(
    task: str,
    constraints: dict[str, Any],
    candidates: list[dict[str, Any]],
    requested_caps: list[str] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    try:
        raw = _generate_sales_json(
            task=task,
            constraints=constraints,
            candidates=candidates,
            requested_caps=requested_caps,
            history=history,
            strict=False,
            response_format="json",
        )
    except OllamaConnectionError as e:
        raise SalesAgentError(str(e)) from e

    payload = _safe_json_load(raw)
    if payload is None:
        # Retry with a strict prompt and compact candidate payload.
        compact_candidates = [
            {
                "app_id": c.get("app_id"),
                "name": c.get("name"),
                "capabilities": c.get("capabilities", []),
                "freshness": c.get("freshness"),
                "citations_supported": c.get("citations_supported"),
                "latency_est_ms": c.get("latency_est_ms"),
                "cost_est_usd": c.get("cost_est_usd"),
            }
            for c in candidates
        ]
        try:
            raw = _generate_sales_json(
                task=task,
                constraints=constraints,
                candidates=compact_candidates,
                requested_caps=requested_caps,
                history=history,
                strict=True,
                response_format=None,
            )
            payload = _safe_json_load(raw)
        except Exception:
            payload = None
        if payload is None:
            try:
                payload = _repair_json(
                    raw,
                    {
                        "summary": "string",
                        "final_choice": "string",
                        "recommendations": [
                            {"app_id": "string", "rationale": "string", "tradeoff": "string"}
                        ],
                    },
                )
            except Exception as e:
                raise SalesAgentError("sales_agent_invalid_json") from e
    try:
        return _parse_sales_payload(payload, candidates)
    except SalesAgentError as e:
        last_error = e
        allowed_ids = [c.get("app_id") for c in candidates if c.get("app_id")]
        try:
            repaired = _repair_sales_payload(raw, task, candidates, allowed_ids)
            return _parse_sales_payload(repaired, candidates)
        except Exception as e2:
            raise SalesAgentError(str(last_error)) from e2


def sales_no_match(
    task: str,
    constraints: dict[str, Any],
    history: list[dict[str, Any]] | None = None,
) -> dict[str, str]:
    try:
        raw = ollama_generate(
            SALES_AGENT_MODEL,
            NO_MATCH_PROMPT.format(
                task=task,
                constraints_json=json.dumps(constraints, ensure_ascii=True),
                history_json=json.dumps(history or [], ensure_ascii=True),
            ),
            options={
                "temperature": SALES_AGENT_TEMPERATURE,
                "num_predict": SALES_AGENT_MAX_TOKENS,
            },
            response_format="json",
            timeout=SALES_AGENT_TIMEOUT,
        )
    except OllamaConnectionError as e:
        raise SalesAgentError(str(e)) from e

    payload = _safe_json_load(raw)
    if payload is None:
        try:
            payload = _repair_json(
                raw,
                {"message": "string"},
            )
        except Exception as e:
            raise SalesAgentError("sales_agent_invalid_json") from e
    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise SalesAgentError("sales_agent_invalid_no_match_message")
    return {"message": message.strip()}
