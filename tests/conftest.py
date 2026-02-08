import os
import pytest

# Must be set before any marketplace imports
os.environ["DATABASE_URL"] = "sqlite:///./test_marketplace.db"


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
    """Mock sales agent functions to avoid Ollama dependency in tests."""
    # Import is delayed until first test runs, allowing test files to set env vars first
    import apps.api.main as api_main
    api_main.sales_recommendation = _mock_sales_recommendation
    api_main.sales_no_match = _mock_sales_no_match
    yield
