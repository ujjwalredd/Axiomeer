from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple

from marketplace.core.models import ShopRequest, Recommendation
from marketplace.settings import W_CAP, W_LAT, W_COST

def _norm_capabilities(caps: Iterable[str]) -> set[str]:
    return {c.strip().lower() for c in caps if c and c.strip()}

def _capability_match(required: set[str], app_caps: set[str]) -> float:
    """
    Returns coverage of required capabilities:
    1.0 means app covers all required caps
    0.0 means covers none
    """
    if not required:
        return 1.0  # if user didn't specify, don't punish
    covered = len(required & app_caps)
    return covered / len(required)

def _latency_score(lat_ms: int, max_ms: int | None) -> float:
    """
    Score in [0,1]. If max_ms is given, penalize as it approaches max.
    If no max, use a soft curve that favors lower latency.
    """
    lat_ms = max(1, int(lat_ms))
    if max_ms and max_ms > 0:
        # if app exceeds max, it should already be filtered out
        # score linearly: 1 at 1ms, 0 at max_ms
        return max(0.0, min(1.0, 1.0 - (lat_ms - 1) / (max_ms - 1)))
    # soft: 1 at 1ms, ~0.5 at 500ms, lower as it grows
    return 1.0 / (1.0 + (lat_ms / 500.0))

def _cost_score(cost: float, max_cost: float | None) -> float:
    cost = max(0.0, float(cost))
    if max_cost is not None:
        if max_cost == 0:
            return 1.0 if cost == 0 else 0.0
        # 1.0 if free, 0.0 if equals max_cost
        return max(0.0, min(1.0, 1.0 - cost / max_cost))
    # if no constraint, prefer cheaper but don’t over-penalize
    return 1.0 / (1.0 + cost)

def recommend(
    req: ShopRequest,
    apps: List[dict],
    k: int = 3
) -> Tuple[List[Recommendation], List[str]]:
    """
    apps: list of dicts with keys:
      id, name, description, capabilities(list[str]), freshness, citations_supported,
      latency_est_ms, cost_est_usd
    """
    required_caps = _norm_capabilities(req.required_capabilities)
    constraints = req.constraints

    # ---- Hard filters ----
    filtered = []
    for a in apps:
        app_caps = _norm_capabilities(a["capabilities"])

        # freshness
        if constraints.freshness and a["freshness"] != constraints.freshness:
            continue

        # citations support
        if constraints.citations_required and not a["citations_supported"]:
            continue

        # latency
        if constraints.max_latency_ms is not None and a["latency_est_ms"] > constraints.max_latency_ms:
            continue

        # cost
        if constraints.max_cost_usd is not None and a["cost_est_usd"] > constraints.max_cost_usd:
            continue

        # required capabilities: we allow partial matches but score them lower
        filtered.append((a, app_caps))

    if not filtered:
        reasons = [
            "No apps satisfied the hard constraints (freshness/citations/budget/latency).",
            "Try relaxing constraints or adding more apps to the catalog.",
        ]
        return [], reasons

    # ---- Score and rank ----
    scored: List[tuple[float, dict, list[str]]] = []
    for a, app_caps in filtered:
        cap = _capability_match(required_caps, app_caps)
        lat = _latency_score(a["latency_est_ms"], constraints.max_latency_ms)
        cost = _cost_score(a["cost_est_usd"], constraints.max_cost_usd)

        score = (W_CAP * cap) + (W_LAT * lat) + (W_COST * cost)

        why = []
        if required_caps:
            why.append(f"Capability match: {cap:.2f} (covers {sorted(required_caps & app_caps)})")
            missing = sorted(required_caps - app_caps)
            if missing:
                why.append(f"Missing: {missing}")
        else:
            why.append("No required_capabilities specified; not penalized on capability coverage.")

        if constraints.freshness:
            why.append(f"Freshness matches requirement: {a['freshness']}")
        if constraints.citations_required:
            why.append("Supports citations/provenance: yes")
        why.append(f"Estimated latency: {a['latency_est_ms']}ms")
        why.append(f"Estimated cost: ${a['cost_est_usd']:.4f}")

        scored.append((score, a, why))

    scored.sort(key=lambda t: t[0], reverse=True)
    top = scored[:k]

    recs = [
        Recommendation(app_id=a["id"], name=a["name"], score=round(score, 3), why=why[:5])
        for score, a, why in top
    ]
    return recs, ["Ranked apps by capability match (primary), then latency, then cost."]
