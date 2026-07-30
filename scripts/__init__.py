"""Scripts package for operational tools."""

# We keep this file minimal to avoid import errors.
# Scripts are intended to be run via `python -m scripts.run_migrations` or `python -m scripts.seed_knowledge_base`.

__all__ = [
    "run_migrations",
    "seed_knowledge_base",
]