"""SQLAlchemy models for risk scores, drivers, and recommendations."""

from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import Float, ForeignKey, Integer, String, Text, UniqueConstraint, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.persistence.models.base import Base


class DecisionModel(Base):
    """Risk scores table (one current score per finding)."""

    __tablename__ = "risk_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    finding_id: Mapped[str] = mapped_column(String(36), nullable=False, unique=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    bis: Mapped[float] = mapped_column(Float, nullable=False)
    tier: Mapped[str] = mapped_column(String(20), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    computed_at: Mapped[int] = mapped_column(Integer, nullable=False)
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0.0")

    __table_args__ = (UniqueConstraint("finding_id", name="uq_risk_scores_finding"),)


class ScoreDriversModel(Base):
    """Drivers breakdown for a risk score."""

    __tablename__ = "score_drivers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    risk_score_id: Mapped[str] = mapped_column(String(36), nullable=False)
    factor: Mapped[str] = mapped_column(String(50), nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    weight: Mapped[float] = mapped_column(Float, nullable=False)


class RecommendationModel(Base):
    """Recommendations table."""

    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    finding_id: Mapped[str] = mapped_column(String(36), nullable=False)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    technical_text: Mapped[str] = mapped_column(Text, nullable=False)
    business_explanation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    estimated_effort: Mapped[str] = mapped_column(String(20), nullable=False)
    estimated_impact: Mapped[int] = mapped_column(Integer, nullable=False)
    risk_reduction_potential: Mapped[float] = mapped_column(Float, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("finding_id", name="uq_recommendations_finding"),)