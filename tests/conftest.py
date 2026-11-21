"""
AutoInsight360 - pytest Configuration
=======================================
Provides shared fixtures for the test suite.

Tests use an in-memory SQLite database so they are:
- Isolated from the production/development database.
- Fast (no disk I/O).
- Idempotent (each test session starts fresh).
"""

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from backend.app.database.base import Base
from backend.app.database import models  # noqa: F401 — registers all models


# ---------------------------------------------------------------------------
# In-memory test database
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def engine():
    """Create a fresh in-memory SQLite engine for the test session."""
    test_engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
    )

    # Enable FK enforcement in test database too
    @event.listens_for(test_engine, "connect")
    def _set_fk(dbapi_connection, _record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()

    Base.metadata.create_all(bind=test_engine)
    yield test_engine
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="session")
def db_session(engine):
    """
    Session-scoped database session with seeded data.

    Seeding is performed once per test session for performance.
    Individual tests MUST NOT commit destructive changes.
    """
    import random

    from backend.app.database.seed_data import (
        RANDOM_SEED,
        seed_customers,
        seed_dealers,
        seed_loyalty_events,
        seed_reviews,
        seed_service_visits,
        seed_transactions,
        seed_vehicles,
    )

    Session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    session = Session()

    rng = random.Random(RANDOM_SEED)
    dealers = seed_dealers(session)
    customers = seed_customers(session, rng, count=20)   # smaller set for tests
    vehicles = seed_vehicles(session, rng, customers)
    transactions = seed_transactions(session, rng, customers, vehicles, dealers, target_count=60)
    seed_service_visits(session, rng, vehicles, dealers, target_count=40)
    seed_loyalty_events(session, rng, customers, transactions, target_count=60)
    seed_reviews(session, rng, customers, dealers, vehicles, target_count=30)

    yield session
    session.close()
