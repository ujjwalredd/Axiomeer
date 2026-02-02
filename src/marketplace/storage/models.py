from sqlalchemy import String, Integer, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column
from marketplace.storage.db import Base

class AppListing(Base):
    __tablename__ = "apps"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    # Stored as comma-separated tags in v1 (simple + good enough)
    capabilities: Mapped[str] = mapped_column(String, nullable=False, default="")

    freshness: Mapped[str] = mapped_column(String, nullable=False, default="static")
    citations_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    latency_est_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    cost_est_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # v1 executor (HTTP API only)
    executor_type: Mapped[str] = mapped_column(String, nullable=False, default="http_api")
    executor_url: Mapped[str] = mapped_column(String, nullable=False, default="")
