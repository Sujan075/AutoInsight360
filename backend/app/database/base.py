"""
AutoInsight360 - Database Base
================================
Declares the SQLAlchemy declarative base used by all ORM models.
Keeping this in a separate module prevents circular imports when
models are split across multiple files in later phases.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared declarative base for all AutoInsight360 ORM models.
    All model classes must inherit from this base so that
    SQLAlchemy can discover them when creating tables.
    """
    pass
