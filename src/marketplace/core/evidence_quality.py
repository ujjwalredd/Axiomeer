from typing import Any, Literal

Quality = Literal["HIGH", "MEDIUM", "LOW"]

def assess_evidence(payload: Any) -> tuple[Quality, list[str]]:
    """
    Deterministic assessment: no LLM.
    """
    reasons: list[str] = []

    if not isinstance(payload, dict):
        return "LOW", ["Evidence is not a JSON object."]

    # If provider explicitly says it's mock/simulated -> LOW
    quality = str(payload.get("quality", "")).lower()
    if quality in {"mock", "simulated", "fake", "test"}:
        return "LOW", [f"Provider marked quality={quality}."]

    ans = str(payload.get("answer", "")).lower()
    if "mock data" in ans or "simulated" in ans or "dummy" in ans:
        reasons.append("Answer text indicates mock/simulated data.")

    cites = payload.get("citations", [])
    if not isinstance(cites, list) or len(cites) == 0:
        reasons.append("No citations found.")

    # If we have any strong red flags -> LOW
    if reasons:
        return "LOW", reasons

    return "HIGH", ["Evidence appears non-mock and contains citations."]
