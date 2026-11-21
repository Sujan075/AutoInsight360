"""
AutoInsight360 - Database Initialisation Script
=================================================
Creates the database, tables, and optionally seeds synthetic data.

Usage
-----
  # Initialise database and seed data (safe – will not overwrite existing):
  python scripts/init_db.py

  # Reset (drop + recreate + seed) — requires explicit confirmation:
  python scripts/init_db.py --reset

  # Initialise without seeding:
  python scripts/init_db.py --no-seed

This script must be run from the project root (AutoInsight360/).

Safety
------
- Without --reset, existing data is NEVER deleted.
- With --reset, the user must type 'yes' to confirm destruction of data.
- Uses ORM operations only; no raw SQL string interpolation.
"""

import argparse
import logging
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make the project root importable from the script directory
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.connection import SessionLocal, get_database_path
from backend.app.database.init_db import create_tables, drop_tables, verify_schema
from backend.app.database.seed_data import seed_database

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("init_db")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AutoInsight360 — Database Initialisation Script"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop all tables and re-create from scratch. DESTRUCTIVE — requires confirmation.",
    )
    parser.add_argument(
        "--no-seed",
        action="store_true",
        help="Create tables but do not seed synthetic data.",
    )
    return parser.parse_args()


def confirm_reset() -> bool:
    """Ask the user to confirm a destructive reset operation."""
    print("\n" + "=" * 60)
    print("  WARNING: --reset will PERMANENTLY DELETE all existing data.")
    print("  The database will be dropped and recreated from scratch.")
    print("=" * 60)
    answer = input("\n  Type 'yes' to confirm, or anything else to cancel: ").strip()
    return answer.lower() == "yes"


def main() -> None:
    args = parse_args()
    db_path = get_database_path()

    logger.info("AutoInsight360 — Database Initialisation")
    logger.info("Database path: %s", db_path)

    # -- Handle reset --------------------------------------------------------
    if args.reset:
        if not confirm_reset():
            logger.info("Reset cancelled by user.")
            sys.exit(0)
        logger.warning("Resetting database...")
        drop_tables()
        logger.info("Tables dropped.")

    # -- Create tables -------------------------------------------------------
    create_tables()

    # -- Verify schema -------------------------------------------------------
    schema_check = verify_schema()
    if not schema_check["ok"]:
        logger.error("Schema verification failed! Missing tables: %s", schema_check["missing"])
        sys.exit(1)
    logger.info("Schema verified. Tables: %s", schema_check["found"])

    # -- Seed data -----------------------------------------------------------
    if args.no_seed:
        logger.info("Seeding skipped (--no-seed flag set).")
    else:
        logger.info("Seeding synthetic data...")
        db = SessionLocal()
        try:
            counts = seed_database(db, reset=args.reset)
            print("\n" + "=" * 50)
            print("  Synthetic Data Seed Results")
            print("=" * 50)
            for table, count in counts.items():
                print(f"  {table:<25} {count:>6} records")
            print("=" * 50)
        finally:
            db.close()

    logger.info("Database initialisation complete.")
    logger.info("Database file: %s", db_path)


if __name__ == "__main__":
    main()
