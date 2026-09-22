"""
app/core/database.py
====================
SQLAlchemy database setup for VoxOps backend.

HOW IT WORKS:
- We create one Engine connected to PostgreSQL.
- SessionLocal is a factory that creates database sessions.
- get_db() is a FastAPI dependency: routes use it to get/close sessions automatically.
- Base is the parent class for all SQLAlchemy models (User, etc.)
"""

# pyrefly: ignore [missing-import]
from sqlalchemy import create_engine
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Generator

from app.core.config import settings


# ── Engine ─────────────────────────────────────────────────────────────────
# The engine is the core interface to the database.
# pool_pre_ping=True checks the connection is alive before each use.
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.DEBUG,  # logs SQL statements when DEBUG=true — helpful for learning!
)


# ── Session Factory ─────────────────────────────────────────────────────────
# SessionLocal creates database sessions.
# autocommit=False means we must call session.commit() explicitly (safe default).
# autoflush=False means changes aren't sent to DB until commit.
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ── Declarative Base ────────────────────────────────────────────────────────
# All SQLAlchemy models (like User) must inherit from this Base.
# It tracks all models so Alembic can auto-generate migrations.
class Base(DeclarativeBase):
    pass


# ── FastAPI Dependency ───────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session to route handlers.

    Usage in a route:
        def my_route(db: Session = Depends(get_db)):
            ...

    The session is automatically closed after the request, even if an error occurs.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
