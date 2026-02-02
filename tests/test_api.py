import pytest
from fastapi.testclient import TestClient

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
    return TestClient(app)


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
    "executor_url": "http://127.0.0.1:8000/providers/weather",
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
        assert r.json() == []

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
    def test_shop_no_apps(self, client):
        r = client.post("/shop", json={
            "task": "Get weather",
            "required_capabilities": ["weather"],
            "constraints": {"citations_required": False},
        })
        assert r.status_code == 200
        assert r.json()["status"] == "NO_MATCH"

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
        assert data["recommendations"][0]["app_id"] == "test_weather"


class TestProvidersEndpoints:
    def test_weather_provider(self, client):
        r = client.get("/providers/weather")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "citations" in data
        assert "retrieved_at" in data
        assert data["quality"] == "mock"

    def test_static_weather_provider(self, client):
        r = client.get("/providers/static-weather")
        assert r.status_code == 200
        data = r.json()
        assert "answer" in data
        assert "citations" in data


class TestRunsEndpoint:
    def test_runs_empty(self, client):
        r = client.get("/runs")
        assert r.status_code == 200
        assert r.json() == []
