from typing import Any, List

def validate_output(payload: Any, require_citations: bool) -> List[str]:
    errors: List[str] = []

    if not isinstance(payload, dict):
        errors.append("Provider output must be a JSON object.")
        return errors

    if require_citations:
        cites = payload.get("citations", None)
        if not isinstance(cites, list) or len(cites) == 0 or not all(isinstance(x, str) and x.strip() for x in cites):
            errors.append("Citations required but missing or invalid. Expected non-empty list field: citations: [str].")

    # optional: require timestamp if citations required
    if require_citations:
        ts = payload.get("retrieved_at", None)
        if not isinstance(ts, str) or not ts.strip():
            errors.append("Citations required but retrieved_at timestamp is missing.")

    return errors
