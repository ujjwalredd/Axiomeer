"""
/shop route — semantic + sales-agent assisted recommendation.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from apps.api.dependencies import cache_get, cache_key, cache_set, get_db, scoped_client_id
from apps.api.services import history_for_client, log_message, trust_scores_by_app
from marketplace.auth.dependencies import check_user_rate_limit
from marketplace.core.models import (
    Recommendation,
    SalesAgentMessage,
    SalesAgentRecommendation,
    ShopRequest,
    ShopResponse,
)
from marketplace.core.router import recommend
from marketplace.llm.sales_agent import SalesAgentError, sales_recommendation
from marketplace.settings import MEMORY_MAX_MESSAGES, SALES_AGENT_TOP_K, SHOP_CACHE_TTL_SECONDS
from marketplace.storage.models import AppListing
from marketplace.storage.users import UsageRecord, User

router = APIRouter(tags=["shop"])


@router.post("/shop", response_model=ShopResponse)
def shop(
    req: ShopRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(check_user_rate_limit),
) -> ShopResponse:
    if current_user.id > 0:
        usage = UsageRecord(user_id=current_user.id, endpoint="/shop", method="POST", cost_usd=0.0)
        db.add(usage)
        db.commit()

    key = cache_key(
        "shop",
        {
            "task": req.task,
            "required_capabilities": sorted([c.strip().lower() for c in req.required_capabilities]),
            "constraints": req.constraints.model_dump(),
        },
    )
    cached = cache_get(key)
    if cached:
        return ShopResponse(**cached)

    history: list[dict] = []
    scoped_id = scoped_client_id(req.client_id, current_user)
    if scoped_id:
        history = history_for_client(db, scoped_id, MEMORY_MAX_MESSAGES)

    trust_scores = trust_scores_by_app(db)
    rows = db.query(AppListing).all()
    apps = []
    for r in rows:
        trust = trust_scores.get(r.id)
        apps.append({
            "id": r.id,
            "name": r.name,
            "description": r.description,
            "capabilities": [c for c in r.capabilities.split(",") if c],
            "freshness": r.freshness,
            "citations_supported": r.citations_supported,
            "latency_est_ms": r.latency_est_ms,
            "cost_est_usd": r.cost_est_usd,
            "trust_score": trust.trust_score if trust else None,
        })

    # Drop providers currently quarantined by the auto-quarantine background task.
    from marketplace.core.quarantine import filter_apps
    apps = filter_apps(apps)

    semantic_engine = getattr(request.app.state, "semantic_search", None)
    recs, router_expl, router_metrics = recommend(
        req, apps, k=len(apps), semantic_search_engine=semantic_engine,
    )

    if not recs:
        message = router_expl[0] if router_expl else "No suitable products matched strict routing thresholds."
        if scoped_id:
            log_message(db, scoped_id, "client", req.task)
            log_message(db, scoped_id, "sales_agent", message)
        res = ShopResponse(
            status="NO_MATCH",
            recommendations=[],
            explanation=[message],
            sales_agent=SalesAgentMessage(summary=message, final_choice="NO_MATCH", recommendations=[]),
            metrics=router_metrics,
        )
        cache_set(key, res.model_dump(), SHOP_CACHE_TTL_SECONDS)
        return res

    app_lookup = {a["id"]: a for a in apps}
    candidates = []
    for r in recs:
        a = app_lookup.get(r.app_id, {})
        candidates.append({
            "app_id": r.app_id,
            "name": r.name,
            "score": r.score,
            "capabilities": a.get("capabilities", []),
            "freshness": a.get("freshness"),
            "citations_supported": a.get("citations_supported"),
            "latency_est_ms": a.get("latency_est_ms"),
            "cost_est_usd": a.get("cost_est_usd"),
            "trust_score": a.get("trust_score"),
        })

    candidates_for_sales = candidates[: max(1, SALES_AGENT_TOP_K)]

    try:
        sales = sales_recommendation(
            task=req.task,
            constraints=req.constraints.model_dump(),
            candidates=candidates_for_sales,
            requested_caps=req.required_capabilities,
            history=history,
        )
    except SalesAgentError as e:
        summary = f"Sales agent failed: {e}. Returning NO_MATCH to avoid unsafe selection."
        if scoped_id:
            log_message(db, scoped_id, "client", req.task)
            log_message(db, scoped_id, "sales_agent", summary)
        res = ShopResponse(
            status="NO_MATCH",
            recommendations=[],
            explanation=[summary],
            sales_agent=SalesAgentMessage(summary=summary, final_choice="NO_MATCH", recommendations=[]),
            metrics=router_metrics,
        )
        cache_set(key, res.model_dump(), SHOP_CACHE_TTL_SECONDS)
        return res

    if sales["final_choice"] == "NO_MATCH":
        if scoped_id:
            log_message(db, scoped_id, "client", req.task)
            log_message(db, scoped_id, "sales_agent", sales["summary"])
        res = ShopResponse(
            status="NO_MATCH",
            recommendations=[],
            explanation=[sales["summary"]],
            sales_agent=SalesAgentMessage(
                summary=sales["summary"], final_choice="NO_MATCH", recommendations=[],
            ),
            metrics=router_metrics,
        )
        cache_set(key, res.model_dump(), SHOP_CACHE_TTL_SECONDS)
        return res

    chosen_id = sales["final_choice"]
    sales_recs = sales["recommendations"]
    sales_order = {r["app_id"]: i for i, r in enumerate(sales_recs)}
    sales_details = {r["app_id"]: r for r in sales_recs}

    recs_enriched: list[Recommendation] = []
    for r in recs:
        if r.app_id in sales_details:
            details = sales_details[r.app_id]
            r = r.model_copy(update={
                "rationale": details.get("rationale"),
                "tradeoff": details.get("tradeoff"),
            })
        if not r.rationale or not r.tradeoff:
            rationale_bits: list[str] = []
            tradeoff_bits: list[str] = []
            for line in r.why:
                if line.startswith(("Capability match", "Freshness matches", "Supports citations")):
                    rationale_bits.append(line)
                if line.startswith(("Estimated latency", "Estimated cost")):
                    tradeoff_bits.append(line)
            update_fields: dict[str, str | None] = {}
            if not r.rationale and rationale_bits:
                update_fields["rationale"] = "; ".join(rationale_bits)
            if not r.tradeoff and tradeoff_bits:
                update_fields["tradeoff"] = "; ".join(tradeoff_bits)
            if update_fields:
                r = r.model_copy(update=update_fields)
        recs_enriched.append(r)

    recs_sorted = sorted(
        recs_enriched[: max(1, SALES_AGENT_TOP_K)],
        key=lambda r: (0, sales_order[r.app_id]) if r.app_id in sales_order else (1, 0),
    )

    if scoped_id:
        log_message(db, scoped_id, "client", req.task)
        log_message(db, scoped_id, "sales_agent", f"Final choice: {chosen_id}. {sales['summary']}")

    sales_agent_msg = SalesAgentMessage(
        summary=sales["summary"],
        final_choice=chosen_id,
        recommendations=[
            SalesAgentRecommendation(
                app_id=r["app_id"], rationale=r["rationale"], tradeoff=r["tradeoff"],
            )
            for r in sales["recommendations"]
        ],
    )

    res = ShopResponse(
        status="OK",
        recommendations=recs_sorted,
        explanation=[sales["summary"]],
        sales_agent=sales_agent_msg,
        metrics=router_metrics,
    )
    cache_set(key, res.model_dump(), SHOP_CACHE_TTL_SECONDS)
    return res
