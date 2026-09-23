"""
app/models/__init__.py
=======================
Export all SQLAlchemy models so Alembic autogenerate can detect them.

IMPORTANT: Every new model must be imported here AND in alembic/env.py.
"""

from app.models.organization import Organization            # noqa: F401
from app.models.user import User, UserRole, UserStatus     # noqa: F401
from app.models.refresh_token import RefreshToken          # noqa: F401
from app.models.password_reset_token import PasswordResetToken  # noqa: F401
from app.models.invite_token import InviteToken            # noqa: F401
from app.models.knowledge_base import KnowledgeBaseDocument  # noqa: F401
from app.models.email_verification_token import EmailVerificationToken  # noqa: F401
