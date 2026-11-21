"""
AutoInsight360 - Database Initialisation
==========================================
Provides functions to create tables and verify the database schema.

Usage
-----
Called by scripts/init_db.py to initialise and optionally seed the database.

Safety
------
- Tables are only created; existing tables are never silently dropped.
- A reset operation requires explicit confirmation via the --reset flag.
- Uses ORM / parameterised queries; no raw string interpolation.
"""

import logging

from sqlalchemy import inspect, text

from .base import Base
from .connection import engine
from .migrations import run_schema_migrations

logger = logging.getLogger(__name__)

# Import all models so that Base.metadata is fully populated before
# create_all is called.  Without this import, models defined in models.py
# are not registered against the metadata.
from . import models  # noqa: F401, E402  (side-effect import)


def create_tables(target_engine=None) -> None:
    """
    Create all database tables defined in the ORM models.

    Uses checkfirst=True (default via create_all) so existing tables
    are left untouched.  Safe to call multiple times.
    Also executes additive schema migrations.
    """
    bind_engine = target_engine or engine
    logger.info("Creating database tables (if not already present)...")
    Base.metadata.create_all(bind=bind_engine)
    run_schema_migrations(bind_engine)
    logger.info("Tables created and migrations applied successfully.")


def drop_tables() -> None:
    """
    Drop all database tables.

    WARNING: This permanently deletes all data.
    Only call this when an explicit --reset flag has been confirmed.
    """
    logger.warning("Dropping all database tables — all data will be lost.")
    Base.metadata.drop_all(bind=engine)
    logger.warning("All tables dropped.")


def get_existing_table_names() -> list[str]:
    """Return a list of table names currently present in the database."""
    inspector = inspect(engine)
    return inspector.get_table_names()


def verify_schema() -> dict:
    """
    Check that the expected tables exist and return a summary dict.

    Returns
    -------
    dict with keys:
        'ok'      : bool — True if all expected tables are present
        'found'   : list[str] — tables found in the database
        'missing' : list[str] — expected tables not found
    """
    expected = {
        "dealers",
        "customers",
        "vehicles",
        "transactions",
        "service_visits",
        "loyalty_events",
        "customer_reviews",
    }
    found = set(get_existing_table_names())
    missing = expected - found
    return {
        "ok": len(missing) == 0,
        "found": sorted(found),
        "missing": sorted(missing),
    }
