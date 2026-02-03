import os

# Must be set before any marketplace imports
os.environ["DATABASE_URL"] = "sqlite:///./test_marketplace.db"


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests that require network access")
