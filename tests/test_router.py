from marketplace.core.models import ShopRequest, Constraints
from marketplace.core.router import (
    recommend,
    _capability_match,
    _latency_score,
    _cost_score,
)


SAMPLE_APPS = [
    {
        "id": "weather_rt",
        "name": "Realtime Weather",
        "description": "Realtime weather with citations",
        "capabilities": ["weather", "realtime", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "latency_est_ms": 800,
        "cost_est_usd": 0.0,
    },
    {
        "id": "weather_static",
        "name": "Static Weather",
        "description": "Static weather data",
        "capabilities": ["weather"],
        "freshness": "static",
        "citations_supported": False,
        "latency_est_ms": 100,
        "cost_est_usd": 0.0,
    },
    {
        "id": "finance_rt",
        "name": "Finance Realtime",
        "description": "Realtime finance data",
        "capabilities": ["finance", "realtime", "citations"],
        "freshness": "realtime",
        "citations_supported": True,
        "latency_est_ms": 500,
        "cost_est_usd": 0.005,
    },
]


class TestCapabilityMatch:
    def test_full_match(self):
        assert _capability_match({"weather", "realtime"}, {"weather", "realtime", "citations"}) == 1.0

    def test_partial_match(self):
        score = _capability_match({"weather", "realtime"}, {"weather"})
        assert score == 0.5

    def test_no_match(self):
        assert _capability_match({"finance"}, {"weather"}) == 0.0

    def test_empty_required(self):
        assert _capability_match(set(), {"weather"}) == 1.0


class TestLatencyScore:
    def test_low_latency_high_score(self):
        assert _latency_score(1, None) > 0.9

    def test_high_latency_low_score(self):
        assert _latency_score(5000, None) < 0.2

    def test_within_max(self):
        score = _latency_score(100, 1000)
        assert 0.0 < score <= 1.0

    def test_at_max(self):
        score = _latency_score(1000, 1000)
        assert score <= 0.01


class TestCostScore:
    def test_free_is_best(self):
        assert _cost_score(0.0, None) == 1.0

    def test_free_with_max(self):
        assert _cost_score(0.0, 0.01) == 1.0

    def test_at_max_cost(self):
        assert _cost_score(0.01, 0.01) == 0.0

    def test_zero_max_free(self):
        assert _cost_score(0.0, 0.0) == 1.0

    def test_zero_max_nonzero_cost(self):
        assert _cost_score(0.01, 0.0) == 0.0


class TestRecommend:
    def test_basic_recommendation(self):
        req = ShopRequest(
            task="Get weather",
            required_capabilities=["weather"],
            constraints=Constraints(citations_required=False),
        )
        recs, explanation, metrics = recommend(req, SAMPLE_APPS, k=3)
        assert len(recs) >= 1
        assert all(r.score >= 0.0 and r.score <= 1.0 for r in recs)

    def test_freshness_filter(self):
        req = ShopRequest(
            task="Get realtime weather",
            required_capabilities=["weather"],
            constraints=Constraints(freshness="realtime", citations_required=False),
        )
        recs, _, _ = recommend(req, SAMPLE_APPS, k=3)
        assert all(r.app_id != "weather_static" for r in recs)

    def test_citations_filter(self):
        req = ShopRequest(
            task="Get weather",
            required_capabilities=["weather"],
            constraints=Constraints(citations_required=True),
        )
        recs, _, _ = recommend(req, SAMPLE_APPS, k=3)
        assert all(r.app_id != "weather_static" for r in recs)

    def test_latency_filter(self):
        req = ShopRequest(
            task="Get weather",
            required_capabilities=["weather"],
            constraints=Constraints(citations_required=False, max_latency_ms=200),
        )
        recs, _, _ = recommend(req, SAMPLE_APPS, k=3)
        assert all(r.app_id != "weather_rt" for r in recs)

    def test_cost_filter(self):
        req = ShopRequest(
            task="Get finance data",
            required_capabilities=["finance"],
            constraints=Constraints(citations_required=False, max_cost_usd=0.001),
        )
        recs, _, _ = recommend(req, SAMPLE_APPS, k=3)
        assert all(r.app_id != "finance_rt" for r in recs)

    def test_no_match_returns_empty(self):
        """Router requires full capability coverage when required_capabilities is set."""
        req = ShopRequest(
            task="Translate text",
            required_capabilities=["translate"],
            constraints=Constraints(freshness="realtime", citations_required=True),
        )
        recs, reasons, _ = recommend(req, SAMPLE_APPS, k=3)
        assert recs == []

    def test_top_k_limit(self):
        req = ShopRequest(
            task="Get data",
            required_capabilities=[],
            constraints=Constraints(citations_required=False),
        )
        recs, _, _ = recommend(req, SAMPLE_APPS, k=1)
        assert len(recs) == 1

    def test_weather_rt_ranked_first_for_weather_realtime(self):
        req = ShopRequest(
            task="Get realtime weather",
            required_capabilities=["weather", "realtime"],
            constraints=Constraints(citations_required=True, freshness="realtime"),
        )
        recs, _, _ = recommend(req, SAMPLE_APPS, k=3)
        assert recs[0].app_id == "weather_rt"
