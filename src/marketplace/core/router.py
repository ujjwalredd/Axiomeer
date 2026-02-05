from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable, List, Tuple
import math
import re

from marketplace.core.models import ShopRequest, Recommendation
from marketplace.settings import (
    W_CAP,
    W_LAT,
    W_COST,
    W_TRUST,
    W_REL,
    MIN_CAP_COVERAGE,
    MIN_RELEVANCE_SCORE,
    MIN_TOTAL_SCORE,
)

def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())

def _build_tfidf_vectors(task: str, docs: list[str]) -> tuple[dict[str, float], list[dict[str, float]]]:
    task_tokens = _tokenize(task)
    doc_tokens = [ _tokenize(d) for d in docs ]
    all_docs = [task_tokens] + doc_tokens
    df: dict[str, int] = {}
    for tokens in all_docs:
        for t in set(tokens):
            df[t] = df.get(t, 0) + 1
    n = len(all_docs)
    idf = {t: math.log((n + 1) / (df_t + 1)) + 1.0 for t, df_t in df.items()}

    def tfidf(tokens: list[str]) -> dict[str, float]:
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        vec: dict[str, float] = {}
        for t, c in tf.items():
            vec[t] = (c / len(tokens)) * idf.get(t, 0.0)
        return vec

    task_vec = tfidf(task_tokens) if task_tokens else {}
    doc_vecs = [tfidf(tokens) if tokens else {} for tokens in doc_tokens]
    return task_vec, doc_vecs

def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    if not a or not b:
        return 0.0
    common = set(a.keys()) & set(b.keys())
    dot = sum(a[t] * b[t] for t in common)
    norm_a = math.sqrt(sum(v * v for v in a.values()))
    norm_b = math.sqrt(sum(v * v for v in b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))

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

        filtered.append((a, app_caps))

    if not filtered:
        return [], []

    # ---- Relevance (text similarity) ----
    docs = []
    for a, _ in filtered:
        desc = a.get("description", "")
        name = a.get("name", "")
        caps = " ".join(a.get("capabilities", []))
        docs.append(f"{name} {desc} {caps}".strip())
    task_vec, doc_vecs = _build_tfidf_vectors(req.task, docs)
    relevance_scores = [_cosine(task_vec, dv) for dv in doc_vecs]

    # ---- Score and rank ----
    scored: List[tuple[float, dict, list[str]]] = []
    for idx, (a, app_caps) in enumerate(filtered):
        cap = _capability_match(required_caps, app_caps)
        lat = _latency_score(a["latency_est_ms"], constraints.max_latency_ms)
        cost = _cost_score(a["cost_est_usd"], constraints.max_cost_usd)
        rel = relevance_scores[idx] if idx < len(relevance_scores) else 0.0

        if required_caps and cap < MIN_CAP_COVERAGE:
            continue
        if rel < MIN_RELEVANCE_SCORE:
            continue

        trust_raw = a.get("trust_score")
        try:
            trust = float(trust_raw) if trust_raw is not None else 0.5
        except (TypeError, ValueError):
            trust = 0.5
        trust = max(0.0, min(1.0, trust))

        total_weight = W_CAP + W_LAT + W_COST + W_TRUST + W_REL
        if total_weight <= 0:
            total_weight = 1.0
        score = (
            (W_CAP * cap)
            + (W_LAT * lat)
            + (W_COST * cost)
            + (W_TRUST * trust)
            + (W_REL * rel)
        ) / total_weight

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
        if W_TRUST > 0:
            why.append(f"Trust score: {trust:.2f}")
        if W_REL > 0:
            why.append(f"Relevance score: {rel:.2f}")
        why.append(f"Estimated latency: {a['latency_est_ms']}ms")
        why.append(f"Estimated cost: ${a['cost_est_usd']:.4f}")

        scored.append((score, a, why))

    if not scored:
        if required_caps:
            return [], [f"No apps met minimum capability coverage ({MIN_CAP_COVERAGE:.2f})."]
        return [], [f"No apps met minimum relevance score ({MIN_RELEVANCE_SCORE:.2f})."]

    scored.sort(key=lambda t: t[0], reverse=True)
    if scored and scored[0][0] < MIN_TOTAL_SCORE:
        return [], [f"Top score {scored[0][0]:.2f} below minimum {MIN_TOTAL_SCORE:.2f}."]
    top = scored[:k]

    recs = [
        Recommendation(
            app_id=a["id"],
            name=a["name"],
            score=round(score, 3),
            why=why[:5],
            trust_score=a.get("trust_score"),
        )
        for score, a, why in top
    ]
    return recs, []
