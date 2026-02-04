from sqlalchemy import String, Integer, Boolean, Text, Float
from sqlalchemy.orm import Mapped, mapped_column
from marketplace.storage.db import Base

class Run(Base):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    app_id: Mapped[str] = mapped_column(String, nullable=False)
    task: Mapped[str] = mapped_column(Text, nullable=False)
    client_id: Mapped[str | None] = mapped_column(String, nullable=True)

    require_citations: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    ok: Mapped[bool] = mapped_column(Boolean, nullable=False)

    # store JSON strings for v1 simplicity
    output_json: Mapped[str] = mapped_column(Text, nullable=True)
    validation_errors_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")

    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[str] = mapped_column(String, nullable=False)  # ISO timestamp
