import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./marketplace.db")

# API
API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Ollama
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "30"))
ROUTER_MODEL: str = os.getenv("ROUTER_MODEL", "llama2:7b")
ANSWER_MODEL: str = os.getenv("ANSWER_MODEL", "llama2:7b")

# Router scoring weights
W_CAP: float = float(os.getenv("W_CAP", "0.70"))
W_LAT: float = float(os.getenv("W_LAT", "0.20"))
W_COST: float = float(os.getenv("W_COST", "0.10"))
