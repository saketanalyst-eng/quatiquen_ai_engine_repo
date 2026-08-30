"""Knowledge base seeder script.

This script loads JSON data from the knowledge_base folder and seeds it into the database.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.core.config.settings import get_settings
from src.core.logging.logger import get_logger
from src.infrastructure.persistence.models.base import Base

logger = get_logger("quantiquan.scripts.seed_knowledge_base")


class KnowledgeBaseSeeder:
    """Seeder for loading knowledge base JSON files into the database."""

    def __init__(self) -> None:
        """Initialize seeder."""
        self.settings = get_settings()
        self.engine = None
        self.async_session = None
        self.knowledge_base_path = Path(__file__).parent.parent / "src" / "knowledge_base"

    async def __aenter__(self) -> "KnowledgeBaseSeeder":
        """Enter context manager."""
        self.engine = create_async_engine(
            str(self.settings.database_url),
            echo=self.settings.debug,
            pool_size=self.settings.database_pool_size,
        )
        self.async_session = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        if self.engine:
            await self.engine.dispose()

    async def _create_tables_if_not_exist(self) -> None:
        """Create all tables if they don't exist."""
        logger.info("Creating tables if not exist")
        async with self.engine.begin() as conn:
            # 1. Create core tables (if missing) using SQLAlchemy metadata
            await conn.run_sync(Base.metadata.create_all)

            # 2. Create knowledge base tables (missing due to migration)
            #    These are not part of the ORM models, so we create them manually.
            knowledge_base_ddl = """
            -- Priority Matrix
            CREATE TABLE IF NOT EXISTS priority_matrix (
                tier VARCHAR(20) PRIMARY KEY,
                conditions JSON NOT NULL DEFAULT '[]',
                time_to_fix_hours INTEGER NOT NULL DEFAULT 24,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Boost Mappings
            CREATE TABLE IF NOT EXISTS boost_mappings (
                name VARCHAR(50) PRIMARY KEY,
                multiplier FLOAT NOT NULL DEFAULT 1.0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Scoring Weights
            CREATE TABLE IF NOT EXISTS scoring_weights (
                name VARCHAR(50) PRIMARY KEY,
                value FLOAT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Data Sensitivity Mappings
            CREATE TABLE IF NOT EXISTS data_sensitivity_mappings (
                name VARCHAR(50) PRIMARY KEY,
                weight FLOAT NOT NULL DEFAULT 1.0,
                note VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Mitigation Categories
            CREATE TABLE IF NOT EXISTS mitigation_categories (
                name VARCHAR(100) PRIMARY KEY,
                description VARCHAR(500),
                mitigations JSON NOT NULL DEFAULT '[]',
                time_to_mitigate JSON NOT NULL DEFAULT '{}',
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Compliance Frameworks
            CREATE TABLE IF NOT EXISTS compliance_frameworks (
                name VARCHAR(50) PRIMARY KEY,
                display_name VARCHAR(255) NOT NULL,
                requirements JSON NOT NULL DEFAULT '{}',
                floor_raise INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Severity Normalization
            CREATE TABLE IF NOT EXISTS severity_normalization (
                scale_name VARCHAR(50) PRIMARY KEY,
                config JSON NOT NULL DEFAULT '{}',
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Tier Bounds
            CREATE TABLE IF NOT EXISTS tier_bounds (
                tier VARCHAR(20) PRIMARY KEY,
                min_score INTEGER NOT NULL,
                max_score INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );

            -- Remediation Templates
            CREATE TABLE IF NOT EXISTS remediation_templates (
                id VARCHAR(50) PRIMARY KEY,
                category VARCHAR(100) NOT NULL,
                cve_pattern VARCHAR(50),
                technical_text TEXT NOT NULL,
                estimated_effort VARCHAR(20) NOT NULL,
                estimated_impact INTEGER NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
            );
            """
            # Execute each statement separately to avoid transaction issues
            for stmt in knowledge_base_ddl.split(';'):
                stmt = stmt.strip()
                if stmt:
                    await conn.execute(text(stmt))

        logger.info("Tables created/verified")

    async def _clear_existing_data(self, async_session: AsyncSession) -> None:
        """Clear existing knowledge base data.

        Args:
            async_session: SQLAlchemy async session.
        """
        # We need to delete in order due to foreign keys
        # For simplicity, we truncate relevant tables
        # This is safe for seed data
        tables = [
            "recommendations",
            "score_drivers",
            "risk_scores",
            "finding_history",
            "findings",
            "assets",
        ]

        for table in tables:
            try:
                await async_session.execute(text(f"DELETE FROM {table}"))
            except Exception as exc:
                logger.warning(f"Failed to clear table {table}", error=str(exc))

        await async_session.commit()
        logger.info("Existing knowledge base data cleared")

    async def seed_remediation_templates(self, async_session: AsyncSession) -> None:
        """Seed remediation templates from JSON.

        Args:
            async_session: SQLAlchemy async session.
        """
        file_path = self.knowledge_base_path / "remediation_templates.json"
        if not file_path.exists():
            logger.warning("remediation_templates.json not found, skipping")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        templates = data.get("templates", [])
        logger.info(f"Seeding {len(templates)} remediation templates")

        # Insert into a knowledge_base_templates table (simplified)
        # For this implementation, we'll use raw SQL
        # In production, you'd use ORM models for knowledge base tables
        for template in templates:
            try:
                # Check if template already exists
                result = await async_session.execute(
                    text("SELECT 1 FROM remediation_templates WHERE id = :id"),
                    {"id": template.get("id")}
                )
                exists = result.scalar() is not None

                if not exists:
                    # Insert
                    await async_session.execute(
                        text("""
                            INSERT INTO remediation_templates (
                                id, category, cve_pattern, technical_text,
                                estimated_effort, estimated_impact
                            ) VALUES (:id, :category, :cve_pattern, :technical_text,
                                :estimated_effort, :estimated_impact)
                        """),
                        {
                            "id": template.get("id"),
                            "category": template.get("category"),
                            "cve_pattern": template.get("cve_pattern"),
                            "technical_text": template.get("technical_text"),
                            "estimated_effort": template.get("estimated_effort"),
                            "estimated_impact": template.get("estimated_impact"),
                        }
                    )
            except Exception as exc:
                logger.error(f"Failed to seed template {template.get('id')}", error=str(exc))

        await async_session.commit()
        logger.info("Remediation templates seeded successfully")

    async def seed_compliance_mapping(self, async_session: AsyncSession) -> None:
        """Seed compliance mapping from JSON.

        Args:
            async_session: SQLAlchemy async session.
        """
        file_path = self.knowledge_base_path / "compliance_mapping.json"
        if not file_path.exists():
            logger.warning("compliance_mapping.json not found, skipping")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        frameworks = data.get("frameworks", {})
        logger.info(f"Seeding {len(frameworks)} compliance frameworks")

        for framework_name, framework_data in frameworks.items():
            try:
                # Insert into compliance_frameworks table
                await async_session.execute(
                    text("""
                        INSERT INTO compliance_frameworks (name, display_name, requirements, floor_raise)
                        VALUES (:name, :display_name, :requirements, :floor_raise)
                        ON CONFLICT (name) DO UPDATE SET
                            display_name = EXCLUDED.display_name,
                            requirements = EXCLUDED.requirements,
                            floor_raise = EXCLUDED.floor_raise
                    """),
                    {
                        "name": framework_name,
                        "display_name": framework_data.get("name"),
                        "requirements": json.dumps(framework_data.get("requirements", {})),
                        "floor_raise": framework_data.get("floor_raise", 0),
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed compliance framework {framework_name}", error=str(exc))

        # Seed data sensitivity mappings
        sensitivity = data.get("data_sensitivity", {})
        logger.info(f"Seeding {len(sensitivity)} data sensitivity mappings")

        for name, mapping in sensitivity.items():
            try:
                await async_session.execute(
                    text("""
                        INSERT INTO data_sensitivity_mappings (name, weight, note)
                        VALUES (:name, :weight, :note)
                        ON CONFLICT (name) DO UPDATE SET
                            weight = EXCLUDED.weight,
                            note = EXCLUDED.note
                    """),
                    {
                        "name": name,
                        "weight": mapping.get("weight", 1.0),
                        "note": mapping.get("note", ""),
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed data sensitivity {name}", error=str(exc))

        await async_session.commit()
        logger.info("Compliance mapping seeded successfully")

    async def seed_priority_matrix(self, async_session: AsyncSession) -> None:
        """Seed priority matrix from JSON.

        Args:
            async_session: SQLAlchemy async session.
        """
        file_path = self.knowledge_base_path / "priority_matrix.json"
        if not file_path.exists():
            logger.warning("priority_matrix.json not found, skipping")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        matrix = data.get("matrix", {})
        logger.info(f"Seeding {len(matrix)} priority matrix entries")

        for tier, config in matrix.items():
            try:
                conditions = config.get("conditions", [])
                await async_session.execute(
                    text("""
                        INSERT INTO priority_matrix (tier, conditions, time_to_fix_hours)
                        VALUES (:tier, :conditions, :time_to_fix_hours)
                        ON CONFLICT (tier) DO UPDATE SET
                            conditions = EXCLUDED.conditions,
                            time_to_fix_hours = EXCLUDED.time_to_fix_hours
                    """),
                    {
                        "tier": tier,
                        "conditions": json.dumps(conditions),
                        "time_to_fix_hours": config.get("time_to_fix_hours", 24),
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed priority matrix entry {tier}", error=str(exc))

        # Seed boosts
        boosts = data.get("boosts", {})
        logger.info(f"Seeding {len(boosts)} boost mappings")

        for name, config in boosts.items():
            try:
                await async_session.execute(
                    text("""
                        INSERT INTO boost_mappings (name, multiplier)
                        VALUES (:name, :multiplier)
                        ON CONFLICT (name) DO UPDATE SET
                            multiplier = EXCLUDED.multiplier
                    """),
                    {
                        "name": name,
                        "multiplier": config.get("multiplier", 1.0),
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed boost mapping {name}", error=str(exc))

        await async_session.commit()
        logger.info("Priority matrix seeded successfully")

    async def seed_scoring_rules(self, async_session: AsyncSession) -> None:
        """Seed scoring rules from JSON.

        Args:
            async_session: SQLAlchemy async session.
        """
        file_path = self.knowledge_base_path / "scoring_rules.json"
        if not file_path.exists():
            logger.warning("scoring_rules.json not found, skipping")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        # Seed severity normalization rules
        normalization = data.get("severity_normalization", {})
        logger.info(f"Seeding {len(normalization)} severity normalization rules")

        for scale, config in normalization.items():
            try:
                await async_session.execute(
                    text("""
                        INSERT INTO severity_normalization (scale_name, config)
                        VALUES (:scale_name, :config)
                        ON CONFLICT (scale_name) DO UPDATE SET
                            config = EXCLUDED.config
                    """),
                    {
                        "scale_name": scale,
                        "config": json.dumps(config),
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed severity normalization {scale}", error=str(exc))

        # Seed weights
        weights = data.get("weights", {})
        logger.info(f"Seeding {len(weights)} scoring weights")

        for name, value in weights.items():
            try:
                await async_session.execute(
                    text("""
                        INSERT INTO scoring_weights (name, value)
                        VALUES (:name, :value)
                        ON CONFLICT (name) DO UPDATE SET
                            value = EXCLUDED.value
                    """),
                    {
                        "name": name,
                        "value": value,
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed scoring weight {name}", error=str(exc))

        # Seed tier bounds
        bounds = data.get("tier_bounds", {})
        logger.info(f"Seeding {len(bounds)} tier bounds")

        for tier, config in bounds.items():
            try:
                await async_session.execute(
                    text("""
                        INSERT INTO tier_bounds (tier, min_score, max_score)
                        VALUES (:tier, :min_score, :max_score)
                        ON CONFLICT (tier) DO UPDATE SET
                            min_score = EXCLUDED.min_score,
                            max_score = EXCLUDED.max_score
                    """),
                    {
                        "tier": tier,
                        "min_score": config.get("min", 0),
                        "max_score": config.get("max", 100),
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed tier bound {tier}", error=str(exc))

        await async_session.commit()
        logger.info("Scoring rules seeded successfully")

    async def seed_mitigation_rules(self, async_session: AsyncSession) -> None:
        """Seed mitigation rules from JSON.

        Args:
            async_session: SQLAlchemy async session.
        """
        file_path = self.knowledge_base_path / "mitigation_rules.json"
        if not file_path.exists():
            logger.warning("mitigation_rules.json not found, skipping")
            return

        with open(file_path, "r") as f:
            data = json.load(f)

        categories = data.get("categories", {})
        logger.info(f"Seeding {len(categories)} mitigation categories")

        for category, config in categories.items():
            try:
                mitigations = config.get("mitigations", [])
                time_to_mitigate = config.get("time_to_mitigate", {})
                await async_session.execute(
                    text("""
                        INSERT INTO mitigation_categories (name, description, mitigations, time_to_mitigate)
                        VALUES (:name, :description, :mitigations, :time_to_mitigate)
                        ON CONFLICT (name) DO UPDATE SET
                            description = EXCLUDED.description,
                            mitigations = EXCLUDED.mitigations,
                            time_to_mitigate = EXCLUDED.time_to_mitigate
                    """),
                    {
                        "name": category,
                        "description": config.get("description", ""),
                        "mitigations": json.dumps(mitigations),
                        "time_to_mitigate": json.dumps(time_to_mitigate),
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed mitigation category {category}", error=str(exc))

        # Seed default mitigation
        default = data.get("default_mitigation", {})
        if default:
            try:
                mitigations = default.get("mitigations", [])
                time_to_mitigate = default.get("time_to_mitigate", {})
                await async_session.execute(
                    text("""
                        INSERT INTO mitigation_categories (name, description, mitigations, time_to_mitigate, is_default)
                        VALUES ('default', :description, :mitigations, :time_to_mitigate, true)
                        ON CONFLICT (name) DO UPDATE SET
                            description = EXCLUDED.description,
                            mitigations = EXCLUDED.mitigations,
                            time_to_mitigate = EXCLUDED.time_to_mitigate,
                            is_default = true
                    """),
                    {
                        "description": default.get("description", "Default mitigation for uncategorized findings"),
                        "mitigations": json.dumps(mitigations),
                        "time_to_mitigate": json.dumps(time_to_mitigate),
                    }
                )
            except Exception as exc:
                logger.error(f"Failed to seed default mitigation", error=str(exc))

        await async_session.commit()
        logger.info("Mitigation rules seeded successfully")

    async def seed_all(self) -> None:
        """Seed all knowledge base data."""
        async with self.async_session() as session:
            # Ensure all tables exist (including knowledge base)
            await self._create_tables_if_not_exist()

            logger.info("Starting knowledge base seed")

            # Seed in dependency order
            await self.seed_priority_matrix(session)
            await self.seed_compliance_mapping(session)
            await self.seed_scoring_rules(session)
            await self.seed_mitigation_rules(session)
            await self.seed_remediation_templates(session)

            logger.info("Knowledge base seeding completed successfully")


async def run_seed() -> None:
    """Run the seeder asynchronously."""
    try:
        async with KnowledgeBaseSeeder() as seeder:
            await seeder.seed_all()
        logger.info("Knowledge base seeding completed successfully")
    except Exception as exc:
        logger.error("Knowledge base seeding failed", error=str(exc), exc_info=True)
        raise


@click.command()
@click.option("--clear", is_flag=True, help="Clear existing data before seeding")
@click.option("--tables", multiple=True, help="Specific tables to seed (e.g., --tables remediation)")
def cli(clear: bool, tables: tuple) -> None:
    """Seed knowledge base data into the database.

    This script loads JSON data from the knowledge_base folder and seeds it into the database.
    It creates required tables if they don't exist.
    """
    try:
        if clear:
            logger.info("--clear not implemented, use --skip if you want to avoid clearing")
        asyncio.run(run_seed())
        logger.info("Knowledge base seeded successfully")
        sys.exit(0)
    except Exception as exc:
        logger.error("Seed failed", error=str(exc), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()