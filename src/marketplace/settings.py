import os
from dotenv import load_dotenv

load_dotenv()

# Database
DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./marketplace.db")

# API
API_BASE_URL: str = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")

# Ollama
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "60"))
ROUTER_MODEL: str = os.getenv("ROUTER_MODEL", "qwen2.5:14b-instruct")
ANSWER_MODEL: str = os.getenv("ANSWER_MODEL", "qwen2.5:14b-instruct")
SALES_AGENT_MODEL: str = os.getenv("SALES_AGENT_MODEL", "phi3.5:3.8b")
SALES_AGENT_MAX_TOKENS: int = int(os.getenv("SALES_AGENT_MAX_TOKENS", "200"))
SALES_AGENT_TEMPERATURE: float = float(os.getenv("SALES_AGENT_TEMPERATURE", "0.0"))
SALES_AGENT_TIMEOUT: int = int(os.getenv("SALES_AGENT_TIMEOUT", "60"))

# Router scoring weights
W_CAP: float = float(os.getenv("W_CAP", "0.70"))
W_LAT: float = float(os.getenv("W_LAT", "0.20"))
W_COST: float = float(os.getenv("W_COST", "0.10"))
W_TRUST: float = float(os.getenv("W_TRUST", "0.15"))
W_REL: float = float(os.getenv("W_REL", "0.25"))

# Router strictness thresholds
MIN_CAP_COVERAGE: float = float(os.getenv("MIN_CAP_COVERAGE", "1.0"))
MIN_RELEVANCE_SCORE: float = float(os.getenv("MIN_RELEVANCE_SCORE", "0.08"))
MIN_TOTAL_SCORE: float = float(os.getenv("MIN_TOTAL_SCORE", "0.55"))
SALES_AGENT_TOP_K: int = int(os.getenv("SALES_AGENT_TOP_K", "8"))

# Conversation memory
MEMORY_MAX_MESSAGES: int = int(os.getenv("MEMORY_MAX_MESSAGES", "6"))

# Provider execution timeout (seconds)
EXECUTOR_TIMEOUT: int = int(os.getenv("EXECUTOR_TIMEOUT", "20"))

# Caching (seconds)
SHOP_CACHE_TTL_SECONDS: int = int(os.getenv("SHOP_CACHE_TTL_SECONDS", "30"))
PROVIDER_CACHE_TTL_WEATHER: int = int(os.getenv("PROVIDER_CACHE_TTL_WEATHER", "30"))
PROVIDER_CACHE_TTL_FX: int = int(os.getenv("PROVIDER_CACHE_TTL_FX", "60"))
PROVIDER_CACHE_TTL_WIKI: int = int(os.getenv("PROVIDER_CACHE_TTL_WIKI", "3600"))
PROVIDER_CACHE_TTL_WIKIDATA: int = int(os.getenv("PROVIDER_CACHE_TTL_WIKIDATA", "3600"))
PROVIDER_CACHE_TTL_WIKIDUMPS: int = int(os.getenv("PROVIDER_CACHE_TTL_WIKIDUMPS", "3600"))
PROVIDER_CACHE_TTL_RESTCOUNTRIES: int = int(os.getenv("PROVIDER_CACHE_TTL_RESTCOUNTRIES", "3600"))
PROVIDER_CACHE_TTL_OPENLIB: int = int(os.getenv("PROVIDER_CACHE_TTL_OPENLIB", "3600"))
PROVIDER_CACHE_TTL_DICTIONARY: int = int(os.getenv("PROVIDER_CACHE_TTL_DICTIONARY", "86400"))
