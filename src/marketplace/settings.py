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
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "phi3.5:3.8b")  # LLM for parameter extraction
ROUTER_MODEL: str = os.getenv("ROUTER_MODEL", "phi3.5:3.8b")
ANSWER_MODEL: str = os.getenv("ANSWER_MODEL", "phi3.5:3.8b")
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

# Semantic Search
SEMANTIC_SEARCH_ENABLED: bool = os.getenv("SEMANTIC_SEARCH_ENABLED", "true").lower() in ("true", "1", "yes")
SEMANTIC_SEARCH_TOP_K: int = int(os.getenv("SEMANTIC_SEARCH_TOP_K", "20"))
SEMANTIC_SEARCH_TIMEOUT_MS: int = int(os.getenv("SEMANTIC_SEARCH_TIMEOUT_MS", "1000"))
SEMANTIC_SEARCH_MODEL: str = os.getenv("SEMANTIC_SEARCH_MODEL", "all-MiniLM-L6-v2")

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

# Authentication
AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "false").lower() in ("true", "1", "yes")
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
API_KEY_HEADER: str = os.getenv("API_KEY_HEADER", "X-API-Key")

# Security validation: Fail fast if auth enabled but no secure JWT secret
if AUTH_ENABLED and not JWT_SECRET_KEY:
    raise RuntimeError(
        "SECURITY ERROR: AUTH_ENABLED=true but JWT_SECRET_KEY is not set. "
        "Generate a secure secret with: python -c \"import secrets; print(secrets.token_urlsafe(32))\""
    )
if AUTH_ENABLED and len(JWT_SECRET_KEY) < 32:
    raise RuntimeError(
        f"SECURITY ERROR: JWT_SECRET_KEY is too short ({len(JWT_SECRET_KEY)} chars). "
        "Must be at least 32 characters for production security."
    )

# Rate Limiting
RATE_LIMIT_ENABLED: bool = os.getenv("RATE_LIMIT_ENABLED", "false").lower() in ("true", "1", "yes")
RATE_LIMIT_FREE_TIER_PER_HOUR: int = int(os.getenv("RATE_LIMIT_FREE_TIER_PER_HOUR", "100"))
RATE_LIMIT_STARTER_TIER_PER_HOUR: int = int(os.getenv("RATE_LIMIT_STARTER_TIER_PER_HOUR", "1000"))
RATE_LIMIT_PRO_TIER_PER_HOUR: int = int(os.getenv("RATE_LIMIT_PRO_TIER_PER_HOUR", "10000"))
