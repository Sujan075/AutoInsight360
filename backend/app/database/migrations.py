"""
AutoInsight360 - Database Migrations
======================================
Provides safe, idempotent additive migrations for SQLite.
Ensures new schema columns exist in existing SQLite databases without
dropping tables or destroying existing records.
"""

import logging
from sqlalchemy import Engine, inspect, text

logger = logging.getLogger(__name__)


def run_schema_migrations(engine: Engine) -> dict[str, list[str]]:
    """
    Apply additive schema changes to the SQLite database.
    Safe to execute on every application startup.

    Returns a summary of columns added per table.
    """
    logger.info("Checking database schema for required additive migrations...")
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    added_columns: dict[str, list[str]] = {}

    with engine.connect() as conn:
        # 1. service_visits table enhancements
        if "service_visits" in existing_tables:
            current_cols = {col["name"] for col in inspector.get_columns("service_visits")}
            service_visit_additions = [
                ("customer_complaint", "TEXT"),
                ("diagnosis", "TEXT"),
                ("work_performed", "TEXT"),
                ("service_status", "VARCHAR(30) DEFAULT 'completed'"),
                ("parts_cost", "NUMERIC(10, 2)"),
                ("labour_cost", "NUMERIC(10, 2)"),
                ("service_description", "TEXT"),
                ("odometer_reading", "INTEGER"),
            ]
            added_sv = []
            for col_name, col_type in service_visit_additions:
                if col_name not in current_cols:
                    logger.info("Migrating service_visits: adding column %s (%s)", col_name, col_type)
                    conn.execute(text(f"ALTER TABLE service_visits ADD COLUMN {col_name} {col_type};"))
                    added_sv.append(col_name)
            if added_sv:
                added_columns["service_visits"] = added_sv

        # 2. loyalty_events table enhancements
        if "loyalty_events" in existing_tables:
            current_cols = {col["name"] for col in inspector.get_columns("loyalty_events")}
            loyalty_additions = [
                ("service_visit_id", "INTEGER"),
                ("program_year", "INTEGER"),
            ]
            added_le = []
            for col_name, col_type in loyalty_additions:
                if col_name not in current_cols:
                    logger.info("Migrating loyalty_events: adding column %s (%s)", col_name, col_type)
                    conn.execute(text(f"ALTER TABLE loyalty_events ADD COLUMN {col_name} {col_type};"))
                    added_le.append(col_name)
            if added_le:
                added_columns["loyalty_events"] = added_le

        # 3. customers table check
        if "customers" in existing_tables:
            current_cols = {col["name"] for col in inspector.get_columns("customers")}
            if "date_of_birth" not in current_cols:
                logger.info("Migrating customers: adding column date_of_birth (DATE)")
                conn.execute(text("ALTER TABLE customers ADD COLUMN date_of_birth DATE;"))
                added_columns.setdefault("customers", []).append("date_of_birth")

        conn.commit()

    logger.info("Database schema migration completed. Columns added: %s", added_columns or "None (schema up to date)")
    return added_columns
