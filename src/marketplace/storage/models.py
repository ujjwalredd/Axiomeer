from sqlalchemy import String, Integer, Boolean, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from marketplace.storage.db import Base

class AppListing(Base):
    __tablename__ = "apps"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=False)

    # Enhanced categorization
    category: Mapped[str] = mapped_column(String, nullable=False, default="general")
    subcategory: Mapped[str | None] = mapped_column(String, nullable=True)
    tags: Mapped[str] = mapped_column(String, nullable=False, default="")  # comma-separated

    # Stored as comma-separated tags (simple + good enough)
    capabilities: Mapped[str] = mapped_column(String, nullable=False, default="")

    freshness: Mapped[str] = mapped_column(String, nullable=False, default="static")
    citations_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Product type
    product_type: Mapped[str] = mapped_column(String, nullable=False, default="api")

    latency_est_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=500)
    cost_est_usd: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)

    # Executor (HTTP API only for now)
    executor_type: Mapped[str] = mapped_column(String, nullable=False, default="http_api")
    executor_url: Mapped[str] = mapped_column(String, nullable=False, default="")

    # Optional extra data (JSON as text) - 'metadata' is reserved by SQLAlchemy
    extra_metadata: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
