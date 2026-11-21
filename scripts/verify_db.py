"""
AutoInsight360 - Database Verification Script
==============================================
Verifies the database structure, record counts, referential integrity,
and demonstrates a complete Customer 360 database retrieval.

Usage
-----
  python scripts/verify_db.py

Must be run from the project root (AutoInsight360/).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.database.connection import SessionLocal, get_database_path
from backend.app.database.init_db import verify_schema
from backend.app.database.models import (
    Customer,
    CustomerReview,
    Dealer,
    LoyaltyEvent,
    ServiceVisit,
    Transaction,
    Vehicle,
)

PASS = "  [PASS]"
FAIL = "  [FAIL]"


def run_verification() -> bool:
    db_path = get_database_path()
    print("=" * 60)
    print("  AutoInsight360 — Database Verification")
    print(f"  Database: {db_path}")
    print("=" * 60)

    all_passed = True
    db = SessionLocal()

    try:
        # ----------------------------------------------------------------
        # 1. Schema check
        # ----------------------------------------------------------------
        print("\n[1] Schema Verification")
        schema = verify_schema()
        if schema["ok"]:
            print(f"{PASS} All expected tables present: {schema['found']}")
        else:
            print(f"{FAIL} Missing tables: {schema['missing']}")
            all_passed = False

        # ----------------------------------------------------------------
        # 2. Record counts
        # ----------------------------------------------------------------
        print("\n[2] Record Counts")
        counts = {
            "customers": db.query(Customer).count(),
            "vehicles": db.query(Vehicle).count(),
            "dealers": db.query(Dealer).count(),
            "transactions": db.query(Transaction).count(),
            "service_visits": db.query(ServiceVisit).count(),
            "loyalty_events": db.query(LoyaltyEvent).count(),
            "customer_reviews": db.query(CustomerReview).count(),
        }
        for table, count in counts.items():
            if count > 0:
                print(f"{PASS} {table:<25} {count:>6} records")
            else:
                print(f"{FAIL} {table:<25}      0 records (expected > 0)")
                all_passed = False

        # ----------------------------------------------------------------
        # 3. Foreign key integrity checks
        # ----------------------------------------------------------------
        print("\n[3] Foreign Key Integrity")

        # Vehicles → Customers
        orphan_vehicles = (
            db.query(Vehicle)
            .filter(~Vehicle.customer_id.in_(db.query(Customer.id)))
            .count()
        )
        if orphan_vehicles == 0:
            print(f"{PASS} No orphaned vehicles (all vehicle.customer_id references valid)")
        else:
            print(f"{FAIL} {orphan_vehicles} orphaned vehicle records found")
            all_passed = False

        # Transactions → Customers
        orphan_tx_customers = (
            db.query(Transaction)
            .filter(~Transaction.customer_id.in_(db.query(Customer.id)))
            .count()
        )
        if orphan_tx_customers == 0:
            print(f"{PASS} No orphaned transactions (customer FK valid)")
        else:
            print(f"{FAIL} {orphan_tx_customers} transactions with invalid customer_id")
            all_passed = False

        # Transactions → Dealers
        orphan_tx_dealers = (
            db.query(Transaction)
            .filter(~Transaction.dealer_id.in_(db.query(Dealer.id)))
            .count()
        )
        if orphan_tx_dealers == 0:
            print(f"{PASS} No orphaned transactions (dealer FK valid)")
        else:
            print(f"{FAIL} {orphan_tx_dealers} transactions with invalid dealer_id")
            all_passed = False

        # ServiceVisits → Vehicles
        orphan_svc = (
            db.query(ServiceVisit)
            .filter(~ServiceVisit.vehicle_id.in_(db.query(Vehicle.id)))
            .count()
        )
        if orphan_svc == 0:
            print(f"{PASS} No orphaned service visits (vehicle FK valid)")
        else:
            print(f"{FAIL} {orphan_svc} service visits with invalid vehicle_id")
            all_passed = False

        # LoyaltyEvents → Customers
        orphan_loyalty = (
            db.query(LoyaltyEvent)
            .filter(~LoyaltyEvent.customer_id.in_(db.query(Customer.id)))
            .count()
        )
        if orphan_loyalty == 0:
            print(f"{PASS} No orphaned loyalty events (customer FK valid)")
        else:
            print(f"{FAIL} {orphan_loyalty} loyalty events with invalid customer_id")
            all_passed = False

        # CustomerReviews → Customers
        orphan_reviews = (
            db.query(CustomerReview)
            .filter(~CustomerReview.customer_id.in_(db.query(Customer.id)))
            .count()
        )
        if orphan_reviews == 0:
            print(f"{PASS} No orphaned reviews (customer FK valid)")
        else:
            print(f"{FAIL} {orphan_reviews} reviews with invalid customer_id")
            all_passed = False

        # ----------------------------------------------------------------
        # 4. Customer 360 Query Demonstration
        # ----------------------------------------------------------------
        print("\n[4] Customer 360 Query Demonstration")
        # Pick the first active customer that has vehicles, transactions, etc.
        demo_customer = (
            db.query(Customer)
            .filter(Customer.is_active.is_(True))
            .first()
        )

        if demo_customer:
            print(f"{PASS} Customer retrieved: ID={demo_customer.id}, "
                  f"Name={demo_customer.first_name} {demo_customer.last_name}, "
                  f"Email={demo_customer.email}")

            # Vehicles
            v_count = len(demo_customer.vehicles)
            if v_count > 0:
                print(f"{PASS}   Vehicles: {v_count}")
                for v in demo_customer.vehicles:
                    print(f"          → {v.year} {v.make} {v.model} (VIN: {v.vin})")
            else:
                print(f"  [NOTE]   No vehicles for this customer.")

            # Transactions
            tx_count = len(demo_customer.transactions)
            if tx_count > 0:
                print(f"{PASS}   Transactions: {tx_count}")
                for tx in demo_customer.transactions[:3]:
                    print(f"          → {tx.transaction_date} | {tx.transaction_type} | ${tx.amount}")
                if tx_count > 3:
                    print(f"          … and {tx_count - 3} more")
            else:
                print(f"  [NOTE]   No transactions for this customer.")

            # Service History (via vehicles)
            all_visits = []
            for v in demo_customer.vehicles:
                all_visits.extend(v.service_visits)
            if all_visits:
                print(f"{PASS}   Service visits: {len(all_visits)}")
                for sv in all_visits[:3]:
                    print(f"          → {sv.service_date} | {sv.service_type} | ${sv.cost}")
            else:
                print(f"  [NOTE]   No service visits for this customer's vehicles.")

            # Loyalty Events
            loy_count = len(demo_customer.loyalty_events)
            if loy_count > 0:
                print(f"{PASS}   Loyalty events: {loy_count}, Balance: {demo_customer.loyalty_points_balance} pts")
                for le in demo_customer.loyalty_events[:3]:
                    print(f"          → {le.event_date} | {le.event_type} | {le.points:+} pts")
            else:
                print(f"  [NOTE]   No loyalty events for this customer.")

            # Reviews
            rev_count = len(demo_customer.reviews)
            if rev_count > 0:
                print(f"{PASS}   Reviews: {rev_count}")
                for r in demo_customer.reviews[:2]:
                    print(f"          → {r.review_date} | {r.review_type} | {r.rating}★ | {r.title!r}")
            else:
                print(f"  [NOTE]   No reviews for this customer.")
        else:
            print(f"{FAIL} No active customer found in database.")
            all_passed = False

        # ----------------------------------------------------------------
        # 5. Summary
        # ----------------------------------------------------------------
        print("\n" + "=" * 60)
        if all_passed:
            print("  RESULT: ALL CHECKS PASSED")
        else:
            print("  RESULT: SOME CHECKS FAILED — review output above")
        print("=" * 60)

    finally:
        db.close()

    return all_passed


if __name__ == "__main__":
    passed = run_verification()
    sys.exit(0 if passed else 1)
