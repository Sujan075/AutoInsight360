"""
AutoInsight360 - Database Connection
======================================
Configures the SQLAlchemy engine and session factory for SQLite.

Design decisions:
- SQLite is used for the MVP to keep the stack simple and dependency-free.
- The database URL is derived from the project root so that no absolute
  Windows paths are hardcoded.  The DATA_DIR environment variable can
  override the default location for testing or future migration.
- check_same_thread=False is required for SQLite when FastAPI (or any
  async framework) uses the session across threads.
- A context-manager helper (get_db) is provided for future FastAPI
  dependency injection without coupling this module to FastAPI.
"""

import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Resolve the database path
# ---------------------------------------------------------------------------
# Walk up from this file to the project root (AutoInsight360/).
# Structure: backend/app/database/connection.py  →  3 parents up = project root
_THIS_FILE = Path(__file__).resolve()
_PROJECT_ROOT = _THIS_FILE.parents[3]          # AutoInsight360/
_DEFAULT_DB_DIR = _PROJECT_ROOT / "data"
_DB_DIR = Path(os.environ.get("AUTOINSIGHT_DATA_DIR", str(_DEFAULT_DB_DIR)))
_DB_DIR.mkdir(parents=True, exist_ok=True)

_DB_FILENAME = os.environ.get("AUTOINSIGHT_DB_NAME", "autoinsight360.db")
_DB_PATH = _DB_DIR / _DB_FILENAME

# ---------------------------------------------------------------------------
# SQLAlchemy engine
# ---------------------------------------------------------------------------
DATABASE_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,          # Set to True temporarily to log SQL during debugging
)

# Enable SQLite foreign-key enforcement (disabled by default in SQLite)
@event.listens_for(engine, "connect")
def _set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.close()

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db():
    """
    Context-manager / generator that yields a database session and
    guarantees the session is closed after use.

    Usage in plain Python::

        from backend.app.database.connection import get_db
        with next(get_db()) as db:
            ...

    Future FastAPI usage::

        @app.get("/customers/{customer_id}")
        def read_customer(customer_id: int, db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_database_path() -> Path:
    """Return the resolved path of the SQLite database file."""
    return _DB_PATH
