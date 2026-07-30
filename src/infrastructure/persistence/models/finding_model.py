"""SQLAlchemy model for findings."""

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import Base


class FindingModel(Base):
    """Findings table model."""

    __tablename__ = "findings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    asset_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_finding_id: Mapped[str] = mapped_column(String(255), nullable=False)
    cve_id: Mapped[str] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)
    raw_severity: Mapped[float] = mapped_column(Float, nullable=False)
    raw_severity_scale: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    detected_at: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "source", "source_finding_id", name="uq_finding_source"),
    )


class FindingHistoryModel(Base):
    """Finding history audit table."""

    __tablename__ = "finding_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    finding_id: Mapped[str] = mapped_column(String(36), nullable=False)
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default={})
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())