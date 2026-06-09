from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

Freshness = Literal["static", "daily", "realtime"]
ShopStatus = Literal["OK", "NO_MATCH"]
ProductType = Literal["api", "model", "dataset", "tool", "aggregator"]


class Constraints(BaseModel):
    citations_required: bool = True
    freshness: Freshness | None = None
    max_latency_ms: int | None = Field(default=None, ge=1)
    max_cost_usd: float | None = Field(default=None, ge=0.0)


class ShopRequest(BaseModel):
    task: str = Field(min_length=1, max_length=2000)
    required_capabilities: list[str] = Field(default_factory=list)
    constraints: Constraints = Field(default_factory=Constraints)
    client_id: str | None = Field(default=None, max_length=200)


class Recommendation(BaseModel):
    app_id: str
    name: str
    score: float = Field(ge=0.0, le=1.0)
    why: list[str] = Field(default_factory=list)
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
    recommendations: list[SalesAgentRecommendation] = Field(default_factory=list)

class ShopResponse(BaseModel):
    status: ShopStatus
    recommendations: list[Recommendation] = Field(default_factory=list)
    explanation: list[str] = Field(default_factory=list)
    sales_agent: SalesAgentMessage | None = None
    metrics: dict[str, Any] = Field(default_factory=dict)


class AppCreate(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)

    # Enhanced categorization (optional, backward compatible)
    category: str = Field(default="general", max_length=100)
    subcategory: str | None = Field(default=None, max_length=100)
    tags: list[str] = Field(default_factory=list)

    capabilities: list[str] = Field(default_factory=list)
    freshness: Freshness = "static"
    citations_supported: bool = True

    # Enhanced product type (optional)
    product_type: ProductType = "api"

    latency_est_ms: int = Field(default=500, ge=1)
    cost_est_usd: float = Field(default=0.0, ge=0.0)

    executor_type: Literal["http_api"] = "http_api"
    executor_url: str = Field(default="", max_length=2000)

    # HTTP method for executor (GET or POST)
    http_method: str | None = Field(default="GET", max_length=10)

    # Input schema for LLM parameter extraction (parameters list + optional examples)
    input_schema: dict[str, Any] | None = Field(default=None)

    # Optional metadata
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("executor_url", mode="after")
    @classmethod
    def validate_executor_url(cls, value: str) -> str:
        if not value:
            return value
        from marketplace.core.executor import UnsafeURLError, validate_safe_url
        try:
            return validate_safe_url(value)
        except UnsafeURLError as exc:
            raise ValueError(str(exc)) from exc

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

    @field_validator("tags", mode="before")
    @classmethod
    def normalize_tags(cls, value):
        if value is None:
            return []
        if not isinstance(value, list):
            return []
        cleaned: list[str] = []
        seen = set()
        for item in value:
            if not isinstance(item, str):
                continue
            tag = item.strip().lower()
            if tag and tag not in seen:
                seen.add(tag)
                cleaned.append(tag)
        return cleaned

class AppOut(AppCreate):
    pass

class ExecuteRequest(BaseModel):
    app_id: str
    task: str
    inputs: dict = Field(default_factory=dict)
    fallback_app_ids: list[str] = Field(default_factory=list, description="Ordered list of fallback app IDs to try if the primary fails")

    require_citations: bool = True
    client_id: str | None = Field(default=None, max_length=200)


class WorkflowStep(BaseModel):
    app_id: str
    task: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    output_key: str = Field(default="", description="Key for this step's output, usable in subsequent steps via {key.field}")


class WorkflowRequest(BaseModel):
    steps: list[WorkflowStep] = Field(min_length=1, max_length=10)
    client_id: str | None = Field(default=None, max_length=200)


class WorkflowStepResult(BaseModel):
    step: int
    app_id: str
    ok: bool
    output: dict[str, Any] | None = None
    error: str | None = None


class WorkflowResponse(BaseModel):
    ok: bool
    steps: list[WorkflowStepResult]
    final_output: dict[str, Any] | None = None

class Provenance(BaseModel):
    sources: list[str] = Field(default_factory=list)
    retrieved_at: str  # ISO timestamp
    notes: list[str] = Field(default_factory=list)

class ExecuteResponse(BaseModel):
    app_id: str
    ok: bool
    output: dict | None = None
    provenance: Provenance | None = None
    validation_errors: list[str] = Field(default_factory=list)
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
    client_id: str | None = None

class RunDetailOut(BaseModel):
    id: int
    app_id: str
    task: str
    require_citations: bool
    ok: bool
    latency_ms: int
    created_at: str
    validation_errors: list[str]
    client_id: str | None = None
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
