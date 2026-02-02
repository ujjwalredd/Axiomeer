import os

# Must be set before any marketplace imports
os.environ["DATABASE_URL"] = "sqlite:///./test_marketplace.db"
