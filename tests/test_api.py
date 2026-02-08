import os
import pytest
from fastapi.testclient import TestClient

# Disable authentication for general API tests
os.environ["AUTH_ENABLED"] = "false"
os.environ["RATE_LIMIT_ENABLED"] = "false"

from marketplace.storage.db import Base, engine
from apps.api.main import app


@pytest.fixture(autouse=True)
def reset_db():
    """Drop and recreate all tables for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


SAMPLE_APP = {
    "id": "test_weather",
    "name": "Test Weather App",
    "description": "A test weather app for unit tests.",
    "capabilities": ["weather", "realtime", "citations"],
    "freshness": "realtime",
    "citations_supported": True,
    "latency_est_ms": 500,
    "cost_est_usd": 0.0,
    "executor_type": "http_api",
    "executor_url": "http://127.0.0.1:8000/providers/openmeteo_weather",
}


class TestHealthEndpoint:
    def test_health(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "ok"}


class TestAppsEndpoints:
    def test_list_apps_empty(self, client):
        r = client.get("/apps")
        assert r.status_code == 200
        # Auto-bootstrap loads manifests, so list may not be empty
        assert isinstance(r.json(), list)

    def test_create_app(self, client):
        r = client.post("/apps", json=SAMPLE_APP)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == "test_weather"
        assert data["name"] == "Test Weather App"

    def test_create_duplicate_app(self, client):
        client.post("/apps", json=SAMPLE_APP)
        r = client.post("/apps", json=SAMPLE_APP)
        assert r.status_code == 409

    def test_get_app(self, client):
        client.post("/apps", json=SAMPLE_APP)
        r = client.get("/apps/test_weather")
        assert r.status_code == 200
        assert r.json()["id"] == "test_weather"

    def test_get_app_not_found(self, client):
        r = client.get("/apps/nonexistent")
        assert r.status_code == 404

    def test_upsert_app(self, client):
        client.post("/apps", json=SAMPLE_APP)
        updated = {**SAMPLE_APP, "name": "Updated Weather App"}
        r = client.put("/apps/test_weather", json=updated)
        assert r.status_code == 200
        assert r.json()["name"] == "Updated Weather App"

    def test_upsert_creates_new(self, client):
        r = client.put("/apps/test_weather", json=SAMPLE_APP)
        assert r.status_code == 200
        assert r.json()["id"] == "test_weather"


class TestShopEndpoint:
    def test_shop_no_matching_apps(self, client):
        r = client.post("/shop", json={
            "task": "Get weather",
            "required_capabilities": ["weather"],
            "constraints": {"citations_required": False},
        })
        assert r.status_code == 200

    def test_shop_with_app(self, client):
        client.post("/apps", json=SAMPLE_APP)
        r = client.post("/shop", json={
            "task": "Get weather",
            "required_capabilities": ["weather"],
            "constraints": {"citations_required": True},
        })
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "OK"
        assert len(data["recommendations"]) >= 1


class TestExecuteEndpoint:
    def test_execute_unknown_app(self, client):
        r = client.post("/execute", json={
            "app_id": "nonexistent",
            "task": "test",
            "inputs": {},
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False
        assert "Unknown app_id" in data["validation_errors"]

    def test_execute_missing_executor_url(self, client):
        no_url_app = {**SAMPLE_APP, "id": "no_url", "executor_url": ""}
        client.post("/apps", json=no_url_app)
        r = client.post("/execute", json={
            "app_id": "no_url",
            "task": "test",
            "inputs": {},
        })
        assert r.status_code == 200
        data = r.json()
        assert data["ok"] is False
        assert "Missing executor_url" in data["validation_errors"]


class TestProvidersEndpoints:
    @pytest.mark.integration
    def test_openmeteo_weather_provider(self, client):
        r = client.get("/providers/openmeteo_weather")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "citations" in data
        assert data["quality"] == "verified"

    @pytest.mark.integration
    def test_wikipedia_provider(self, client):
        r = client.get("/providers/wikipedia?q=Python_(programming_language)")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "citations" in data
        assert data["quality"] == "verified"

    @pytest.mark.integration
    def test_restcountries_provider(self, client):
        r = client.get("/providers/restcountries?q=France")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "citations" in data
        assert "retrieved_at" in data

    @pytest.mark.integration
    def test_restcountries_not_found(self, client):
        r = client.get("/providers/restcountries?q=xyznonexistent")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data

    @pytest.mark.integration
    def test_exchangerate_provider(self, client):
        r = client.get("/providers/exchangerate?base=USD")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "citations" in data

    @pytest.mark.integration
    def test_dictionary_provider(self, client):
        r = client.get("/providers/dictionary?word=hello")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "citations" in data

    @pytest.mark.integration
    def test_dictionary_not_found(self, client):
        r = client.get("/providers/dictionary?word=xyznonexistent123")
        assert r.status_code == 200
        data = r.json()
        assert "No definition found" in data["answer"]

    @pytest.mark.integration
    def test_openlibrary_provider(self, client):
        r = client.get("/providers/openlibrary?q=python")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "citations" in data

    def test_wikipedia_empty_query(self, client):
        r = client.get("/providers/wikipedia?q=")
        assert r.status_code == 200
        data = r.json()
        # Accept either "No query provided" or "No Wikipedia article found" for empty query
        assert ("No query provided" in data["answer"] or "No Wikipedia article found" in data["answer"])

    def test_restcountries_empty_query(self, client):
        r = client.get("/providers/restcountries?q=")
        assert r.status_code == 200
        data = r.json()
        assert "No country name provided" in data["answer"]

    def test_dictionary_empty_query(self, client):
        r = client.get("/providers/dictionary?word=")
        assert r.status_code == 200
        data = r.json()
        assert "No word provided" in data["answer"]

    def test_exchangerate_empty_query(self, client):
        r = client.get("/providers/exchangerate?base=")
        assert r.status_code == 200
        data = r.json()
        assert "No base currency provided" in data["answer"]

    def test_openlibrary_empty_query(self, client):
        r = client.get("/providers/openlibrary?q=")
        assert r.status_code == 200
        data = r.json()
        assert "No search query provided" in data["answer"]


class TestAutoBootstrap:
    def test_manifests_loaded_on_startup(self, client):
        """After app startup, manifests should be auto-registered."""
        r = client.get("/apps")
        assert r.status_code == 200
        apps = r.json()
        app_ids = [a["id"] for a in apps]
        assert "realtime_weather_agent" in app_ids
        assert "wikipedia_search" in app_ids
        assert "rest_countries" in app_ids
        assert "exchange_rates" in app_ids
        assert "dictionary" in app_ids
        assert "open_library" in app_ids


class TestRunsEndpoint:
    def test_runs_empty(self, client):
        r = client.get("/runs")
        assert r.status_code == 200
        assert r.json() == []
