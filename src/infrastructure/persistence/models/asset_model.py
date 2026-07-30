"""SQLAlchemy model for assets."""

from datetime import datetime
from typing import List
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import Base


class AssetModel(Base):
    """Assets table model."""

    __tablename__ = "assets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    importance_tier: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), nullable=True)
    data_classification: Mapped[str] = mapped_column(String(50), nullable=False)
    compliance_scopes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=[])
    exposure: Mapped[str] = mapped_column(String(50), nullable=False)
    is_production: Mapped[bool] = mapped_column(nullable=False, default=False)
    downstream_dependents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    revenue_impact: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )