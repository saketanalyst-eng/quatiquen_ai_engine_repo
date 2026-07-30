"""Initial migration for QUANTIQUAN AI ENGINE.

Revision ID: 001
Revises: 
Create Date: 2026-07-27

This migration creates all tables required for the application.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create all tables."""

    # Tenants table
    op.create_table(
        "tenants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )

    # Assets table
    op.create_table(
        "assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("asset_type", sa.String(50), nullable=False),
        sa.Column("importance_tier", sa.Integer, nullable=False, server_default="50"),
        sa.Column("owner_id", sa.String(36), nullable=True),
        sa.Column("data_classification", sa.String(50), nullable=False, server_default="internal"),
        sa.Column("compliance_scopes", sa.JSON, nullable=False, server_default='[]'),
        sa.Column("exposure", sa.String(50), nullable=False, server_default="internal-only"),
        sa.Column("is_production", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("downstream_dependents", sa.Integer, nullable=False, server_default="0"),
        sa.Column("revenue_impact", sa.String(50), nullable=False, server_default="none"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"]),
    )

    # Findings table
    op.create_table(
        "findings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("asset_id", sa.String(36), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_finding_id", sa.String(255), nullable=False),
        sa.Column("cve_id", sa.String(50), nullable=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.String(2000), nullable=False),
        sa.Column("raw_severity", sa.Float, nullable=False),
        sa.Column("raw_severity_scale", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("detected_at", sa.Integer, nullable=False),
        sa.Column("raw_payload", sa.JSON, nullable=False, server_default='{}'),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"]),
        sa.UniqueConstraint("tenant_id", "source", "source_finding_id", name="uq_finding_source"),
    )

    # Finding History table
    op.create_table(
        "finding_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36), nullable=False),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("payload", sa.JSON, nullable=False, server_default='{}'),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
    )

    # Risk Scores table
    op.create_table(
        "risk_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("bis", sa.Float, nullable=False),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("computed_at", sa.Integer, nullable=False),
        sa.Column("version", sa.String(20), nullable=False, server_default="1.0.0"),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )

    # Score Drivers table
    op.create_table(
        "score_drivers",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("risk_score_id", sa.String(36), nullable=False),
        sa.Column("factor", sa.String(50), nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("weight", sa.Float, nullable=False),
        sa.ForeignKeyConstraint(["risk_score_id"], ["risk_scores.id"]),
    )

    # Recommendations table
    op.create_table(
        "recommendations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("finding_id", sa.String(36), nullable=False, unique=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("technical_text", sa.Text, nullable=False),
        sa.Column("business_explanation", sa.Text, nullable=True),
        sa.Column("estimated_effort", sa.String(20), nullable=False),
        sa.Column("estimated_impact", sa.Integer, nullable=False),
        sa.Column("risk_reduction_potential", sa.Float, nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["finding_id"], ["findings.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
    )

    # Knowledge Base tables

    op.create_table(
        "remediation_templates",
        sa.Column("id", sa.String(50), primary_key=True),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("cve_pattern", sa.String(50), nullable=True),
        sa.Column("technical_text", sa.Text, nullable=False),
        sa.Column("estimated_effort", sa.String(20), nullable=False),
        sa.Column("estimated_impact", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "compliance_frameworks",
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("requirements", sa.JSON, nullable=False, server_default='{}'),
        sa.Column("floor_raise", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "data_sensitivity_mappings",
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("weight", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("note", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "priority_matrix",
        sa.Column("tier", sa.String(20), primary_key=True),
        sa.Column("conditions", sa.JSON, nullable=False, server_default='[]'),
        sa.Column("time_to_fix_hours", sa.Integer, nullable=False, server_default="24"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "boost_mappings",
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("multiplier", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "severity_normalization",
        sa.Column("scale_name", sa.String(50), primary_key=True),
        sa.Column("config", sa.JSON, nullable=False, server_default='{}'),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scoring_weights",
        sa.Column("name", sa.String(50), primary_key=True),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tier_bounds",
        sa.Column("tier", sa.String(20), primary_key=True),
        sa.Column("min_score", sa.Integer, nullable=False),
        sa.Column("max_score", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "mitigation_categories",
        sa.Column("name", sa.String(100), primary_key=True),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("mitigations", sa.JSON, nullable=False, server_default='[]'),
        sa.Column("time_to_mitigate", sa.JSON, nullable=False, server_default='{}'),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Drop all tables."""
    op.drop_table("mitigation_categories")
    op.drop_table("tier_bounds")
    op.drop_table("scoring_weights")
    op.drop_table("severity_normalization")
    op.drop_table("boost_mappings")
    op.drop_table("priority_matrix")
    op.drop_table("data_sensitivity_mappings")
    op.drop_table("compliance_frameworks")
    op.drop_table("remediation_templates")
    op.drop_table("recommendations")
    op.drop_table("score_drivers")
    op.drop_table("risk_scores")
    op.drop_table("finding_history")
    op.drop_table("findings")
    op.drop_table("assets")
    op.drop_table("users")
    op.drop_table("tenants")