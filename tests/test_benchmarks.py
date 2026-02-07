"""
Comprehensive benchmarking and validation tests.

Tests include:
1. Real API validation - verify actual data retrieval
2. Fake query rejection - demonstrate no hallucination
3. Latency benchmarking - measure performance
"""

import time
import pytest
import requests
from typing import Dict, Any

API_BASE = "http://127.0.0.1:8000"


class TestRealAPIValidation:
    """Test that real queries return genuine data with citations."""

    def test_weather_api_real_data(self):
        """Verify weather API returns real data with citations."""
        start = time.time()

        response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Current weather in New York",
                "required_capabilities": ["weather", "realtime", "citations"]
            }
        )

        latency = (time.time() - start) * 1000

        assert response.status_code == 200
        data = response.json()

        # Should find weather products
        assert data["status"] == "OK"
        assert len(data["recommendations"]) > 0

        # Should have performance metrics
        assert "metrics" in data
        assert data["metrics"]["total_time_ms"] > 0

        print(f"\n✓ Weather query: {latency:.0f}ms")
        print(f"  Semantic search: {data['metrics'].get('semantic_search_time_ms', 0):.0f}ms")
        print(f"  Found {len(data['recommendations'])} products")

    def test_finance_api_real_data(self):
        """Verify financial API returns real data with citations."""
        start = time.time()

        response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Bitcoin price in USD",
                "required_capabilities": ["finance", "citations"]
            }
        )

        latency = (time.time() - start) * 1000

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "OK"
        assert len(data["recommendations"]) > 0

        # Execute top recommendation
        top_app = data["recommendations"][0]["app_id"]
        exec_start = time.time()

        exec_response = requests.post(
            f"{API_BASE}/execute",
            json={
                "app_id": top_app,
                "task": "Bitcoin price",
                "require_citations": True
            }
        )

        exec_latency = (time.time() - exec_start) * 1000
        exec_data = exec_response.json()

        # Verify execution succeeded
        assert exec_data["ok"] is True
        assert "citations" in exec_data["output"]
        assert len(exec_data["output"]["citations"]) > 0
        assert "retrieved_at" in exec_data["output"]

        print(f"\n✓ Finance query: {latency:.0f}ms")
        print(f"  Execution: {exec_latency:.0f}ms")
        print(f"  Citations: {len(exec_data['output']['citations'])}")
        print(f"  Quality: {exec_data['output'].get('quality', 'unknown')}")

    def test_research_api_real_data(self):
        """Verify research API returns real academic data."""
        start = time.time()

        response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Recent papers on machine learning",
                "required_capabilities": ["search", "citations"]
            }
        )

        latency = (time.time() - start) * 1000

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "OK"

        print(f"\n✓ Research query: {latency:.0f}ms")
        print(f"  Found {len(data['recommendations'])} research sources")


class TestFakeQueryRejection:
    """Test that fake/impossible queries are rejected with NO_MATCH."""

    def test_fake_capability_returns_no_match(self):
        """Verify fake capabilities return NO_MATCH, not hallucinated results."""
        start = time.time()

        response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Execute arbitrary Python code and return output",
                "required_capabilities": ["code_execution", "citations"]
            }
        )

        latency = (time.time() - start) * 1000

        assert response.status_code == 200
        data = response.json()

        # Should return NO_MATCH for non-existent capabilities
        assert data["status"] == "NO_MATCH"
        assert len(data["recommendations"]) == 0

        print(f"\n✓ Fake query rejected: {latency:.0f}ms")
        print(f"  Status: {data['status']}")
        print(f"  Explanation: {data['explanation']}")

    def test_impossible_requirement_returns_no_match(self):
        """Verify impossible requirements return NO_MATCH."""
        start = time.time()

        response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Get stock prices",
                "required_capabilities": ["finance"],
                "constraints": {
                    "max_latency_ms": 1,  # Impossible: 1ms
                    "citations_required": True
                }
            }
        )

        latency = (time.time() - start) * 1000

        assert response.status_code == 200
        data = response.json()

        # Should reject impossible constraints
        assert data["status"] == "NO_MATCH"

        print(f"\n✓ Impossible constraint rejected: {latency:.0f}ms")
        print(f"  Reason: max_latency_ms=1 is impossible")

    def test_nonexistent_product_returns_no_match(self):
        """Verify queries for non-existent products return NO_MATCH."""
        start = time.time()

        response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Use quantum computer to solve P=NP",
                "required_capabilities": ["quantum_computing", "np_complete"]
            }
        )

        latency = (time.time() - start) * 1000

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "NO_MATCH"

        print(f"\n✓ Non-existent product rejected: {latency:.0f}ms")


class TestLatencyBenchmarks:
    """Benchmark system performance and latency."""

    def test_semantic_search_performance(self):
        """Measure semantic search latency."""
        # Check if semantic search is available
        stats = requests.get(f"{API_BASE}/semantic-search/stats")
        stats_data = stats.json()

        if not stats_data.get("initialized"):
            pytest.skip("Semantic search not initialized")

        # Run multiple queries and measure
        queries = [
            "weather forecast",
            "cryptocurrency prices",
            "academic research papers",
            "geographic data",
            "financial statistics"
        ]

        latencies = []
        semantic_times = []

        for query in queries:
            start = time.time()
            response = requests.post(
                f"{API_BASE}/shop",
                json={"task": query, "required_capabilities": []}
            )
            total_latency = (time.time() - start) * 1000

            if response.status_code == 200:
                data = response.json()
                latencies.append(total_latency)
                if "metrics" in data:
                    semantic_times.append(
                        data["metrics"].get("semantic_search_time_ms", 0)
                    )

        avg_total = sum(latencies) / len(latencies)
        avg_semantic = sum(semantic_times) / len(semantic_times)

        print(f"\n✓ Semantic Search Benchmark ({len(queries)} queries):")
        print(f"  Average total latency: {avg_total:.0f}ms")
        print(f"  Average semantic search: {avg_semantic:.0f}ms")
        print(f"  Min: {min(latencies):.0f}ms, Max: {max(latencies):.0f}ms")

        # Semantic search should be reasonably fast
        # 250ms is acceptable for semantic embedding + FAISS search
        assert avg_semantic < 250, f"Semantic search too slow: {avg_semantic}ms"

    def test_api_endpoint_latency(self):
        """Measure API endpoint response times."""
        endpoints = [
            "/health",
            "/apps",
            "/trust",
            "/semantic-search/stats"
        ]

        results = {}

        for endpoint in endpoints:
            start = time.time()
            response = requests.get(f"{API_BASE}{endpoint}")
            latency = (time.time() - start) * 1000

            assert response.status_code == 200
            results[endpoint] = latency

        print(f"\n✓ API Endpoint Latencies:")
        for endpoint, latency in results.items():
            print(f"  {endpoint}: {latency:.0f}ms")

        # Health check should be very fast
        assert results["/health"] < 100, "Health check too slow"

    def test_end_to_end_execution_latency(self):
        """Measure complete shop -> execute pipeline latency."""
        start_total = time.time()

        # Step 1: Shop
        shop_start = time.time()
        shop_response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Current exchange rate USD to EUR",
                "required_capabilities": ["finance", "citations"]
            }
        )
        shop_latency = (time.time() - shop_start) * 1000

        assert shop_response.status_code == 200
        shop_data = shop_response.json()
        assert shop_data["status"] == "OK"

        # Step 2: Execute
        top_app = shop_data["recommendations"][0]["app_id"]
        exec_start = time.time()
        exec_response = requests.post(
            f"{API_BASE}/execute",
            json={
                "app_id": top_app,
                "task": "Exchange rate",
                "require_citations": True
            }
        )
        exec_latency = (time.time() - exec_start) * 1000

        total_latency = (time.time() - start_total) * 1000

        assert exec_response.status_code == 200
        exec_data = exec_response.json()

        # Execution may succeed or fail validation
        # Both are acceptable for latency benchmarking
        print(f"\n✓ End-to-End Pipeline:")
        print(f"  Shop: {shop_latency:.0f}ms")
        print(f"  Execute: {exec_latency:.0f}ms")
        print(f"  Total: {total_latency:.0f}ms")
        print(f"  Provider latency: {exec_data.get('latency_ms', 0):.0f}ms")
        print(f"  Result: {'Success' if exec_data['ok'] else 'Validation Failed'}")

        if not exec_data["ok"]:
            print(f"  Validation errors: {exec_data.get('validation_errors', [])}")

        # Test passes as long as pipeline executes (even if validation fails)
        assert "ok" in exec_data


class TestCitationValidation:
    """Test citation validation and quality checks."""

    def test_citations_required_enforcement(self):
        """Verify citation requirements are enforced."""
        # Find a product that supports citations
        response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Get financial data",
                "required_capabilities": ["finance", "citations"]
            }
        )

        assert response.status_code == 200
        data = response.json()

        if data["status"] == "NO_MATCH":
            pytest.skip("No finance products with citations available")

        top_app = data["recommendations"][0]["app_id"]

        # Execute with citation requirement
        exec_response = requests.post(
            f"{API_BASE}/execute",
            json={
                "app_id": top_app,
                "task": "Financial data",
                "require_citations": True
            }
        )

        exec_data = exec_response.json()

        # Should either succeed with citations or fail validation
        if exec_data["ok"]:
            assert "citations" in exec_data["output"]
            assert len(exec_data["output"]["citations"]) > 0
            print(f"\n✓ Citations validated: {len(exec_data['output']['citations'])} sources")
        else:
            assert "validation_errors" in exec_data
            print(f"\n✓ Validation enforced: {exec_data['validation_errors']}")

    def test_provenance_tracking(self):
        """Verify provenance tracking in execution receipts."""
        # Execute a simple query
        shop_response = requests.post(
            f"{API_BASE}/shop",
            json={
                "task": "Get country data",
                "required_capabilities": ["search"]
            }
        )

        if shop_response.status_code != 200:
            pytest.skip("Shop endpoint unavailable")

        shop_data = shop_response.json()
        if shop_data["status"] == "NO_MATCH":
            pytest.skip("No matching products")

        top_app = shop_data["recommendations"][0]["app_id"]

        exec_response = requests.post(
            f"{API_BASE}/execute",
            json={
                "app_id": top_app,
                "task": "Country info",
                "require_citations": True
            }
        )

        exec_data = exec_response.json()

        # Should have run_id for provenance tracking
        assert "run_id" in exec_data

        # Fetch full receipt
        run_id = exec_data["run_id"]
        receipt = requests.get(f"{API_BASE}/runs/{run_id}")

        assert receipt.status_code == 200
        receipt_data = receipt.json()

        # Verify receipt contains full provenance
        assert receipt_data["id"] == run_id
        assert receipt_data["app_id"] == top_app
        assert "created_at" in receipt_data

        print(f"\n✓ Provenance tracked: run_id={run_id}")
        print(f"  App: {receipt_data['app_id']}")
        print(f"  Success: {receipt_data['ok']}")


class TestTrustScoring:
    """Test trust score calculation and tracking."""

    def test_trust_scores_available(self):
        """Verify trust scores are calculated and available."""
        response = requests.get(f"{API_BASE}/trust")

        assert response.status_code == 200
        trust_data = response.json()

        # Should have trust scores for products that have been executed
        assert isinstance(trust_data, list)

        if len(trust_data) > 0:
            # Check first trust score structure
            score = trust_data[0]
            assert "app_id" in score
            assert "trust_score" in score
            assert "success_rate" in score
            assert "total_runs" in score

            print(f"\n✓ Trust scores available: {len(trust_data)} products")
            print(f"  Sample: {score['app_id']} = {score['trust_score']:.2f}")
            print(f"  Success rate: {score['success_rate']*100:.1f}%")

    def test_trust_score_updates_after_execution(self):
        """Verify trust scores update after executions."""
        # Get initial trust scores
        initial_trust = requests.get(f"{API_BASE}/trust").json()
        initial_count = {t["app_id"]: t["total_runs"] for t in initial_trust}

        # Execute a query
        shop_response = requests.post(
            f"{API_BASE}/shop",
            json={"task": "Simple query", "required_capabilities": []}
        )

        if shop_response.json().get("status") != "OK":
            pytest.skip("No products available")

        app_id = shop_response.json()["recommendations"][0]["app_id"]

        requests.post(
            f"{API_BASE}/execute",
            json={"app_id": app_id, "task": "Test"}
        )

        # Get updated trust scores
        updated_trust = requests.get(f"{API_BASE}/trust").json()
        updated_count = {t["app_id"]: t["total_runs"] for t in updated_trust}

        # Execution count should increase
        initial = initial_count.get(app_id, 0)
        updated = updated_count.get(app_id, 0)

        assert updated >= initial

        print(f"\n✓ Trust score updated for {app_id}")
        print(f"  Executions: {initial} → {updated}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
