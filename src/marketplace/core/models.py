from pydantic import BaseModel, Field, field_validator
from typing import List, Literal, Optional


Freshness = Literal["static", "daily", "realtime"]
ShopStatus = Literal["OK", "NO_MATCH"]


class Constraints(BaseModel):
    citations_required: bool = True
    freshness: Optional[Freshness] = None
    max_latency_ms: Optional[int] = Field(default=None, ge=1)
    max_cost_usd: Optional[float] = Field(default=None, ge=0.0)


class ShopRequest(BaseModel):
    task: str = Field(min_length=1, max_length=2000)
    required_capabilities: List[str] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)
    client_id: Optional[str] = Field(default=None, max_length=200)


class Recommendation(BaseModel):
    app_id: str
    name: str
    score: float = Field(ge=0.0, le=1.0)
    why: List[str] = Field(default_factory=list)
    rationale: str | None = None
    tradeoff: str | None = None
    trust_score: float | None = None

class SalesAgentRecommendation(BaseModel):
    app_id: str
    rationale: str
    tradeoff: str

class SalesAgentMessage(BaseModel):
    summary: str
    final_choice: str
    recommendations: List[SalesAgentRecommendation] = Field(default_factory=list)

class ShopResponse(BaseModel):
    status: ShopStatus
    recommendations: List[Recommendation] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)
    sales_agent: SalesAgentMessage | None = None


class AppCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)

    capabilities: List[str] = Field(default_factory=list)
    freshness: Freshness = "static"
    citations_supported: bool = True

    latency_est_ms: int = Field(default=500, ge=1)
    cost_est_usd: float = Field(default=0.0, ge=0.0)

    executor_type: Literal["http_api"] = "http_api"
    executor_url: str = Field(default="", max_length=2000)

    @field_validator("capabilities", mode="before")
    @classmethod
    def normalize_capabilities(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("capabilities must be a list of strings")
        cleaned: list[str] = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                raise ValueError("capabilities must be a list of strings")
            cap = item.strip().lower()
            if not cap:
                continue
            if cap not in seen:
                seen.add(cap)
                cleaned.append(cap)
        return cleaned

class AppOut(AppCreate):
    pass

class ExecuteRequest(BaseModel):
    app_id: str
    task: str
    inputs: dict = Field(default_factory=dict)

    require_citations: bool = True
    client_id: Optional[str] = Field(default=None, max_length=200)

class Provenance(BaseModel):
    sources: List[str] = Field(default_factory=list)
    retrieved_at: str  # ISO timestamp
    notes: List[str] = Field(default_factory=list)

class ExecuteResponse(BaseModel):
    app_id: str
    ok: bool
    output: dict | None = None
    provenance: Provenance | None = None
    validation_errors: List[str] = Field(default_factory=list)
    run_id: int | None = None

class RunOut(BaseModel):
    id: int
    app_id: str
    task: str
    require_citations: bool
    ok: bool
    latency_ms: int
    created_at: str
    validation_errors: list[str]
    client_id: Optional[str] = None

class RunDetailOut(BaseModel):
    id: int
    app_id: str
    task: str
    require_citations: bool
    ok: bool
    latency_ms: int
    created_at: str
    validation_errors: list[str]
    client_id: Optional[str] = None
    output: dict | None = None

class TrustOut(BaseModel):
    app_id: str
    total_runs: int
    success_rate: float
    citation_pass_rate: float
    avg_latency_ms: int | None = None
    p95_latency_ms: int | None = None
    last_run_at: str | None = None
    trust_score: float
    insufficient_data: bool = False

class MessageIn(BaseModel):
    client_id: str = Field(min_length=1, max_length=200)
    role: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1, max_length=4000)

class MessageOut(BaseModel):
    id: int
    client_id: str
    role: str
    content: str
    created_at: str
