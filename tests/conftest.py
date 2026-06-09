import os

import pytest

# Must be set before any marketplace imports
os.environ["DATABASE_URL"] = "sqlite:///./test_marketplace.db"
# AUTH defaults ON in prod; keep tests deterministic and provide a dummy secret
# so settings.py doesn't fail-fast when AUTH_ENABLED=true.
os.environ.setdefault("AUTH_ENABLED", "false")
os.environ.setdefault("JWT_SECRET_KEY", "test_secret_key_must_be_at_least_32_characters_long")


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests that require network access")


def _mock_sales_recommendation(task, constraints, candidates, requested_caps=None, history=None):
    # Deterministic choice for tests
    return {
        "summary": "test summary",
        "final_choice": candidates[0]["app_id"],
        "recommendations": [
            {
                "app_id": candidates[0]["app_id"],
                "rationale": "test rationale",
                "tradeoff": "test tradeoff",
            }
        ],
    }


def _mock_sales_no_match(task, constraints, history=None):
    return {"message": "test no match"}


@pytest.fixture(scope="session", autouse=True)
def mock_sales_agent():
    """Mock sales agent functions to avoid Ollama dependency in tests.

    Shop handler now lives in apps.api.routers.shop_router (after the main.py
    split). Patch the imported symbol in that namespace.
    """
    import apps.api.routers.shop_router as shop_module
    shop_module.sales_recommendation = _mock_sales_recommendation
    yield
