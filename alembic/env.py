"""
alembic/env.py
==============
Alembic environment configuration.

HOW ALEMBIC WORKS:
- Alembic reads your SQLAlchemy models and compares them to the current database schema.
- When you run `alembic revision --autogenerate -m "some change"`, it creates
  a migration file in alembic/versions/ describing what changed.
- When you run `alembic upgrade head`, it applies all pending migrations.
- When you run `alembic downgrade -1`, it undoes the last migration.

WHAT THIS FILE DOES:
- Reads DATABASE_URL from our .env via app.core.config
- Imports all our models so Alembic knows about them
- Configures the migration runner
"""

import os
import sys
from logging.config import fileConfig

# pyrefly: ignore [missing-import]
from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Make the 'app' package importable ────────────────────────────────────────
# Alembic runs from the 'backend/' directory, so we add it to the Python path.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ── Import our app's database Base and all models ────────────────────────────
# IMPORTANT: You MUST import all models here so Alembic detects them for
# autogenerate. As the team adds more models (Organization, Ticket, etc.),
# they should be imported here too.
from app.core.config import settings      # Load .env variables
from app.core.database import Base        # SQLAlchemy metadata
from app.models.user import User          # noqa: F401 — imported for side effects (registers model)
from app.models.organization import Organization  # noqa: F401
from app.models.department import Department  # noqa: F401
from app.models.job import Job  # noqa: F401


# ── Alembic Config ─────────────────────────────────────────────────────────
config = context.config

# Override the sqlalchemy.url in alembic.ini with our real DATABASE_URL from .env
# ConfigParser uses ``%`` for interpolation. Database URLs commonly contain
# percent-encoded password characters (for example, ``%40`` for ``@``), so
# escape percent signs before handing the URL to Alembic's configuration.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# Set up Python logging from the [loggers] section of alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our models' metadata so autogenerate works
target_metadata = Base.metadata


# ── Migration Runners ─────────────────────────────────────────────────────────

def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (generates SQL without connecting to DB).
    Useful for reviewing what SQL would be executed.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode (connects to DB and applies changes).
    This is the normal mode used by `alembic upgrade head`.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
        )
        with context.begin_transaction():
            context.run_migrations()


# Alembic decides which mode to use based on context
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
