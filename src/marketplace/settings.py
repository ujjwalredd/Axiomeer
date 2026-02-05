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
ROUTER_MODEL: str = os.getenv("ROUTER_MODEL", "qwen2.5:14b-instruct")
ANSWER_MODEL: str = os.getenv("ANSWER_MODEL", "qwen2.5:14b-instruct")
SALES_AGENT_MODEL: str = os.getenv("SALES_AGENT_MODEL", "phi3.5:3.8b")
SALES_AGENT_MAX_TOKENS: int = int(os.getenv("SALES_AGENT_MAX_TOKENS", "120"))
SALES_AGENT_TEMPERATURE: float = float(os.getenv("SALES_AGENT_TEMPERATURE", "0.0"))
SALES_AGENT_TIMEOUT: int = int(os.getenv("SALES_AGENT_TIMEOUT", "12"))

# Router scoring weights
W_CAP: float = float(os.getenv("W_CAP", "0.70"))
W_LAT: float = float(os.getenv("W_LAT", "0.20"))
W_COST: float = float(os.getenv("W_COST", "0.10"))

# Conversation memory
MEMORY_MAX_MESSAGES: int = int(os.getenv("MEMORY_MAX_MESSAGES", "6"))

# Provider execution timeout (seconds)
EXECUTOR_TIMEOUT: int = int(os.getenv("EXECUTOR_TIMEOUT", "20"))
