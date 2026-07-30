"""Alembic migration runner script."""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import alembic.config
import click
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from src.core.config.settings import get_settings
from src.core.logging.logger import get_logger

logger = get_logger("quantiquan.scripts.run_migrations")


def get_alembic_config() -> Config:
    """Get Alembic configuration.

    Returns:
        Config: Alembic configuration object.
    """
    # Find alembic.ini in the project root
    project_root = Path(__file__).parent.parent
    alembic_ini = project_root / "alembic.ini"

    if not alembic_ini.exists():
        # Create default alembic.ini if not exists
        alembic_ini = project_root / "alembic.ini"
        if not alembic_ini.exists():
            logger.warning("alembic.ini not found, creating default")
            _create_default_alembic_ini(alembic_ini, project_root)

    config = alembic.config.Config(str(alembic_ini))
    config.set_main_option("script_location", str(project_root / "src" / "infrastructure" / "persistence" / "migrations"))
    config.set_main_option("prepend_sys_path", str(project_root))

    # Set database URL from settings
    settings = get_settings()
    config.set_main_option("sqlalchemy.url", str(settings.database_url))

    return config


def _create_default_alembic_ini(alembic_ini: Path, project_root: Path) -> None:
    """Create default alembic.ini file.

    Args:
        alembic_ini: Path to alembic.ini.
        project_root: Project root directory.
    """
    content = f"""
[alembic]
script_location = src/infrastructure/persistence/migrations
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = sqlite+aiosqlite:///./quantiquan.db

[post_write_hooks]
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 100

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
    alembic_ini.write_text(content)
    logger.info("Created default alembic.ini", path=str(alembic_ini))


async def _ensure_database_exists() -> None:
    """Ensure the database exists before running migrations.

    For PostgreSQL, it checks and creates the database if needed.
    For SQLite, it does nothing (file is created automatically).
    """
    settings = get_settings()
    db_url = str(settings.database_url)

    # If SQLite, just return – the file is created automatically
    if db_url.startswith("sqlite"):
        logger.info("Using SQLite – database file will be created automatically")
        return

    # PostgreSQL specific: check and create database
    # Extract database name
    db_name = db_url.split("/")[-1]
    base_url = db_url.rsplit("/", 1)[0]

    # Connect to default 'postgres' database to check/create
    try:
        engine = create_async_engine(f"{base_url}/postgres", echo=False)
        async with engine.connect() as conn:
            # Check if database exists
            result = await conn.execute(text(f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"))
            exists = result.scalar() is not None

            if not exists:
                logger.info("Creating database", database=db_name)
                # Database doesn't exist, create it
                # Need to disconnect from default connection first
                await conn.close()
                # Reconnect with autocommit
                engine = create_async_engine(f"{base_url}/postgres", echo=False, isolation_level="AUTOCOMMIT")
                async with engine.connect() as conn2:
                    await conn2.execute(text(f"CREATE DATABASE {db_name}"))
                logger.info("Database created", database=db_name)
            else:
                logger.info("Database already exists", database=db_name)

        await engine.dispose()
    except Exception as exc:
        logger.error("Failed to ensure database exists", error=str(exc), exc_info=True)
        raise


def run_migrations_sync() -> None:
    """Run Alembic migrations (synchronous wrapper)."""
    try:
        config = get_alembic_config()
        command.upgrade(config, "head")
        logger.info("Migrations completed successfully")
    except Exception as exc:
        logger.error("Migration failed", error=str(exc), exc_info=True)
        raise


async def run_migrations_async() -> None:
    """Run Alembic migrations asynchronously."""
    try:
        # Ensure database exists (for PostgreSQL) or skip for SQLite
        await _ensure_database_exists()

        # Run migrations synchronously
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_migrations_sync)

        logger.info("Migrations completed successfully")
    except Exception as exc:
        logger.error("Migration failed", error=str(exc), exc_info=True)
        raise


@click.command()
@click.option("--revision", "-r", default="head", help="Migration revision to upgrade to")
@click.option("--sql", is_flag=True, help="Generate SQL instead of applying migrations")
@click.option("--dry-run", is_flag=True, help="Preview migrations without applying")
def cli(revision: str, sql: bool, dry_run: bool) -> None:
    """Run Alembic migrations.

    This script runs database migrations using Alembic.
    It ensures the database exists before running migrations.
    """
    try:
        if dry_run:
            config = get_alembic_config()
            command.upgrade(config, revision, sql=True)
            logger.info("Dry run completed")
            return

        if sql:
            config = get_alembic_config()
            command.upgrade(config, revision, sql=True)
            return

        # Run async migrations
        asyncio.run(run_migrations_async())
        logger.info("Migrations applied successfully")
        sys.exit(0)
    except Exception as exc:
        logger.error("Migration failed", error=str(exc), exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    cli()