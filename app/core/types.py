"""
app/core/types.py
==================
Custom SQLAlchemy types that work across PostgreSQL AND SQLite.

WHY THIS EXISTS:
- PostgreSQL has a native UUID type.
- SQLite (used in testing) stores UUIDs as strings.
- SQLAlchemy's UUID(as_uuid=True) only works natively with PostgreSQL.
- This GUID type transparently handles both databases.

HOW IT WORKS:
- On PostgreSQL: stores UUID natively.
- On SQLite:  stores UUID as a 32-character hex string.

Usage:
    from app.core.types import GUID

    class MyModel(Base):
        id: Mapped[uuid.UUID] = mapped_column(GUID(), primary_key=True, ...)
"""

import uuid
from sqlalchemy import String, types


class GUID(types.TypeDecorator):
    """
    Platform-independent UUID type.

    Uses PostgreSQL's native UUID type when available,
    otherwise stores as a 32-character hex string (for SQLite).
    """

    impl = types.CHAR(32)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            # Use native UUID for PostgreSQL
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        else:
            # Use 32-char string for SQLite and others
            return dialect.type_descriptor(types.CHAR(32))

    def process_bind_param(self, value, dialect):
        """Convert Python UUID to DB format when saving."""
        if value is None:
            return value
        if dialect.name == "postgresql":
            # PostgreSQL accepts uuid.UUID directly
            return value if isinstance(value, uuid.UUID) else uuid.UUID(str(value))
        else:
            # SQLite: store as hex string without dashes
            if isinstance(value, uuid.UUID):
                return value.hex
            return uuid.UUID(str(value)).hex

    def process_result_value(self, value, dialect):
        """Convert DB value back to Python UUID when loading."""
        if value is None:
            return value
        if isinstance(value, uuid.UUID):
            return value
        return uuid.UUID(str(value))
