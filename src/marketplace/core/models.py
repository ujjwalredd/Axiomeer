from pydantic import BaseModel, Field
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


class ShopResponse(BaseModel):
    status: ShopStatus
    recommendations: List[Recommendation] = Field(default_factory=list)
    explanation: List[str] = Field(default_factory=list)


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
