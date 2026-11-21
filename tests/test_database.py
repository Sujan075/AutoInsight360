"""
AutoInsight360 - Database Tests
=================================
Tests the database schema, relationships, and data integrity.

Run with:
  python -m pytest tests/ -v
"""

import datetime

import pytest
from sqlalchemy.orm import Session

from backend.app.database.models import (
    Customer,
    CustomerReview,
    Dealer,
    LoyaltyEvent,
    ServiceVisit,
    Transaction,
    Vehicle,
)


# ===========================================================================
# 1. Schema Tests
# ===========================================================================

class TestSchema:
    """Verify that the expected tables exist in the database."""

    def test_customers_table_exists(self, db_session: Session):
        result = db_session.query(Customer).limit(1).all()
        assert result is not None

    def test_vehicles_table_exists(self, db_session: Session):
        result = db_session.query(Vehicle).limit(1).all()
        assert result is not None

    def test_dealers_table_exists(self, db_session: Session):
        result = db_session.query(Dealer).limit(1).all()
        assert result is not None

    def test_transactions_table_exists(self, db_session: Session):
        result = db_session.query(Transaction).limit(1).all()
        assert result is not None

    def test_service_visits_table_exists(self, db_session: Session):
        result = db_session.query(ServiceVisit).limit(1).all()
        assert result is not None

    def test_loyalty_events_table_exists(self, db_session: Session):
        result = db_session.query(LoyaltyEvent).limit(1).all()
        assert result is not None

    def test_customer_reviews_table_exists(self, db_session: Session):
        result = db_session.query(CustomerReview).limit(1).all()
        assert result is not None


# ===========================================================================
# 2. Record Count Tests
# ===========================================================================

class TestRecordCounts:
    """Verify that seeded tables contain records."""

    def test_customer_count_greater_than_zero(self, db_session: Session):
        count = db_session.query(Customer).count()
        assert count > 0, f"Expected customers > 0, got {count}"

    def test_vehicle_count_greater_than_zero(self, db_session: Session):
        count = db_session.query(Vehicle).count()
        assert count > 0, f"Expected vehicles > 0, got {count}"

    def test_dealer_count_greater_than_zero(self, db_session: Session):
        count = db_session.query(Dealer).count()
        assert count > 0, f"Expected dealers > 0, got {count}"

    def test_transaction_count_greater_than_zero(self, db_session: Session):
        count = db_session.query(Transaction).count()
        assert count > 0, f"Expected transactions > 0, got {count}"

    def test_service_visit_count_greater_than_zero(self, db_session: Session):
        count = db_session.query(ServiceVisit).count()
        assert count > 0, f"Expected service visits > 0, got {count}"

    def test_loyalty_event_count_greater_than_zero(self, db_session: Session):
        count = db_session.query(LoyaltyEvent).count()
        assert count > 0, f"Expected loyalty events > 0, got {count}"

    def test_customer_review_count_greater_than_zero(self, db_session: Session):
        count = db_session.query(CustomerReview).count()
        assert count > 0, f"Expected reviews > 0, got {count}"


# ===========================================================================
# 3. Data Integrity Tests
# ===========================================================================

class TestDataIntegrity:
    """Verify that generated records have valid field values."""

    def test_customer_email_format(self, db_session: Session):
        """All synthetic customer emails must end with @autoinsight.demo."""
        customers = db_session.query(Customer).limit(10).all()
        for c in customers:
            assert c.email.endswith("@autoinsight.demo"), (
                f"Customer {c.id} email {c.email!r} does not use synthetic domain"
            )

    def test_vehicle_vin_is_synthetic(self, db_session: Session):
        """All VINs must be prefixed with SYNTH- to confirm synthetic data."""
        vehicles = db_session.query(Vehicle).limit(10).all()
        for v in vehicles:
            assert v.vin.startswith("SYNTH-"), (
                f"Vehicle {v.id} VIN {v.vin!r} does not look synthetic"
            )

    def test_vehicle_year_in_valid_range(self, db_session: Session):
        """Vehicle years must be between 1900 and 2100."""
        vehicles = db_session.query(Vehicle).all()
        for v in vehicles:
            assert 1900 <= v.year <= 2100, (
                f"Vehicle {v.id} has out-of-range year {v.year}"
            )

    def test_transaction_amount_non_negative(self, db_session: Session):
        """Transaction amounts must be >= 0."""
        transactions = db_session.query(Transaction).all()
        for tx in transactions:
            assert float(tx.amount) >= 0, (
                f"Transaction {tx.id} has negative amount {tx.amount}"
            )

    def test_service_visit_cost_non_negative(self, db_session: Session):
        """Service visit costs must be >= 0."""
        visits = db_session.query(ServiceVisit).all()
        for sv in visits:
            if sv.cost is not None:
                assert float(sv.cost) >= 0, (
                    f"ServiceVisit {sv.id} has negative cost {sv.cost}"
                )

    def test_review_rating_in_valid_range(self, db_session: Session):
        """Review ratings must be between 1 and 5."""
        reviews = db_session.query(CustomerReview).all()
        for r in reviews:
            assert 1 <= r.rating <= 5, (
                f"CustomerReview {r.id} has out-of-range rating {r.rating}"
            )

    def test_loyalty_event_type_valid(self, db_session: Session):
        """Loyalty event types must be from the allowed set."""
        valid_types = {"earn", "redeem", "adjustment", "expiry", "bonus"}
        events = db_session.query(LoyaltyEvent).all()
        for le in events:
            assert le.event_type in valid_types, (
                f"LoyaltyEvent {le.id} has invalid event_type {le.event_type!r}"
            )

    def test_dealer_emails_synthetic(self, db_session: Session):
        """Dealer emails must use the synthetic domain."""
        dealers = db_session.query(Dealer).all()
        for d in dealers:
            if d.email:
                assert "@autoinsight.demo" in d.email, (
                    f"Dealer {d.id} email {d.email!r} does not use synthetic domain"
                )


# ===========================================================================
# 4. Foreign Key Relationship Tests
# ===========================================================================

class TestForeignKeys:
    """Verify referential integrity between related tables."""

    def test_all_vehicles_have_valid_customer(self, db_session: Session):
        """Every vehicle's customer_id must reference a valid customer."""
        valid_customer_ids = {r[0] for r in db_session.query(Customer.id).all()}
        vehicles = db_session.query(Vehicle).all()
        for v in vehicles:
            assert v.customer_id in valid_customer_ids, (
                f"Vehicle {v.id} has customer_id={v.customer_id} which does not exist"
            )

    def test_all_transactions_have_valid_customer(self, db_session: Session):
        """Every transaction's customer_id must reference a valid customer."""
        valid_customer_ids = {r[0] for r in db_session.query(Customer.id).all()}
        transactions = db_session.query(Transaction).all()
        for tx in transactions:
            assert tx.customer_id in valid_customer_ids, (
                f"Transaction {tx.id} has customer_id={tx.customer_id} which does not exist"
            )

    def test_all_transactions_have_valid_dealer(self, db_session: Session):
        """Every transaction's dealer_id must reference a valid dealer."""
        valid_dealer_ids = {r[0] for r in db_session.query(Dealer.id).all()}
        transactions = db_session.query(Transaction).all()
        for tx in transactions:
            assert tx.dealer_id in valid_dealer_ids, (
                f"Transaction {tx.id} has dealer_id={tx.dealer_id} which does not exist"
            )

    def test_all_service_visits_have_valid_vehicle(self, db_session: Session):
        """Every service visit's vehicle_id must reference a valid vehicle."""
        valid_vehicle_ids = {r[0] for r in db_session.query(Vehicle.id).all()}
        visits = db_session.query(ServiceVisit).all()
        for sv in visits:
            assert sv.vehicle_id in valid_vehicle_ids, (
                f"ServiceVisit {sv.id} has vehicle_id={sv.vehicle_id} which does not exist"
            )

    def test_all_service_visits_have_valid_dealer(self, db_session: Session):
        """Every service visit's dealer_id must reference a valid dealer."""
        valid_dealer_ids = {r[0] for r in db_session.query(Dealer.id).all()}
        visits = db_session.query(ServiceVisit).all()
        for sv in visits:
            assert sv.dealer_id in valid_dealer_ids, (
                f"ServiceVisit {sv.id} has dealer_id={sv.dealer_id} which does not exist"
            )

    def test_all_loyalty_events_have_valid_customer(self, db_session: Session):
        """Every loyalty event's customer_id must reference a valid customer."""
        valid_customer_ids = {r[0] for r in db_session.query(Customer.id).all()}
        events = db_session.query(LoyaltyEvent).all()
        for le in events:
            assert le.customer_id in valid_customer_ids, (
                f"LoyaltyEvent {le.id} has customer_id={le.customer_id} which does not exist"
            )

    def test_all_reviews_have_valid_customer(self, db_session: Session):
        """Every review's customer_id must reference a valid customer."""
        valid_customer_ids = {r[0] for r in db_session.query(Customer.id).all()}
        reviews = db_session.query(CustomerReview).all()
        for r in reviews:
            assert r.customer_id in valid_customer_ids, (
                f"CustomerReview {r.id} has customer_id={r.customer_id} which does not exist"
            )


# ===========================================================================
# 5. Relationship Traversal Tests (ORM)
# ===========================================================================

class TestRelationships:
    """Verify that ORM relationships traverse correctly."""

    def test_customer_has_vehicles_relationship(self, db_session: Session):
        """A customer with vehicles should have accessible vehicle list."""
        # Find a customer who has vehicles
        customer = (
            db_session.query(Customer)
            .join(Vehicle, Vehicle.customer_id == Customer.id)
            .first()
        )
        assert customer is not None, "No customers with vehicles found"
        assert len(customer.vehicles) > 0, (
            f"Customer {customer.id} has no vehicles via relationship"
        )

    def test_customer_has_transactions_relationship(self, db_session: Session):
        """A customer with transactions should have accessible transaction list."""
        customer = (
            db_session.query(Customer)
            .join(Transaction, Transaction.customer_id == Customer.id)
            .first()
        )
        assert customer is not None, "No customers with transactions found"
        assert len(customer.transactions) > 0

    def test_customer_has_loyalty_events_relationship(self, db_session: Session):
        """A customer with loyalty events should traverse the relationship."""
        customer = (
            db_session.query(Customer)
            .join(LoyaltyEvent, LoyaltyEvent.customer_id == Customer.id)
            .first()
        )
        assert customer is not None, "No customers with loyalty events found"
        assert len(customer.loyalty_events) > 0

    def test_vehicle_has_service_visits_relationship(self, db_session: Session):
        """A vehicle with service visits should traverse the relationship."""
        vehicle = (
            db_session.query(Vehicle)
            .join(ServiceVisit, ServiceVisit.vehicle_id == Vehicle.id)
            .first()
        )
        assert vehicle is not None, "No vehicles with service visits found"
        assert len(vehicle.service_visits) > 0

    def test_vehicle_owner_relationship(self, db_session: Session):
        """A vehicle's owner relationship should return the parent customer."""
        vehicle = db_session.query(Vehicle).first()
        assert vehicle is not None
        assert vehicle.owner is not None, "vehicle.owner relationship returned None"
        assert vehicle.owner.id == vehicle.customer_id

    def test_transaction_customer_relationship(self, db_session: Session):
        """A transaction's customer relationship should return the parent customer."""
        tx = db_session.query(Transaction).first()
        assert tx is not None
        assert tx.customer is not None
        assert tx.customer.id == tx.customer_id

    def test_transaction_dealer_relationship(self, db_session: Session):
        """A transaction's dealer relationship should return the parent dealer."""
        tx = db_session.query(Transaction).first()
        assert tx is not None
        assert tx.dealer is not None
        assert tx.dealer.id == tx.dealer_id

    def test_service_visit_vehicle_relationship(self, db_session: Session):
        """A service visit's vehicle relationship should be accessible."""
        sv = db_session.query(ServiceVisit).first()
        assert sv is not None
        assert sv.vehicle is not None
        assert sv.vehicle.id == sv.vehicle_id

    def test_service_visit_dealer_relationship(self, db_session: Session):
        """A service visit's dealer relationship should be accessible."""
        sv = db_session.query(ServiceVisit).first()
        assert sv is not None
        assert sv.dealer is not None
        assert sv.dealer.id == sv.dealer_id


# ===========================================================================
# 6. Customer 360 Query Tests
# ===========================================================================

class TestCustomer360Query:
    """Verify that a full Customer 360 retrieval works end-to-end."""

    def test_customer_360_full_retrieval(self, db_session: Session):
        """
        Demonstrate a complete Customer 360 database retrieval.

        Retrieves a customer and all associated:
        - Vehicles
        - Transactions
        - Service history (via vehicles)
        - Loyalty events
        - Reviews
        """
        customer = db_session.query(Customer).first()
        assert customer is not None, "No customers in database"

        # --- Vehicles ---
        vehicles = customer.vehicles
        assert isinstance(vehicles, list)

        # --- Transactions ---
        transactions = customer.transactions
        assert isinstance(transactions, list)

        # --- Service history via vehicles ---
        all_service_visits = []
        for v in vehicles:
            all_service_visits.extend(v.service_visits)
        assert isinstance(all_service_visits, list)

        # --- Loyalty ---
        loyalty_events = customer.loyalty_events
        assert isinstance(loyalty_events, list)

        # --- Reviews ---
        reviews = customer.reviews
        assert isinstance(reviews, list)

        # This test passes if the traversal completes without error
        # and all related records are of the correct type
        for v in vehicles:
            assert isinstance(v, Vehicle)
        for tx in transactions:
            assert isinstance(tx, Transaction)
        for sv in all_service_visits:
            assert isinstance(sv, ServiceVisit)
        for le in loyalty_events:
            assert isinstance(le, LoyaltyEvent)
        for r in reviews:
            assert isinstance(r, CustomerReview)

    def test_customer_query_by_email(self, db_session: Session):
        """A customer should be retrievable by email."""
        any_customer = db_session.query(Customer).first()
        assert any_customer is not None

        found = (
            db_session.query(Customer)
            .filter(Customer.email == any_customer.email)
            .first()
        )
        assert found is not None
        assert found.id == any_customer.id

    def test_customer_loyalty_balance_non_negative(self, db_session: Session):
        """Customer loyalty_points_balance must be >= 0."""
        customers = db_session.query(Customer).all()
        for c in customers:
            assert c.loyalty_points_balance >= 0, (
                f"Customer {c.id} has negative loyalty balance {c.loyalty_points_balance}"
            )

    def test_primary_vehicle_per_customer(self, db_session: Session):
        """Each customer should have at most one primary vehicle."""
        customers = db_session.query(Customer).all()
        for c in customers:
            primary_count = sum(1 for v in c.vehicles if v.is_primary)
            assert primary_count <= 1, (
                f"Customer {c.id} has {primary_count} primary vehicles (expected ≤ 1)"
            )


# ===========================================================================
# 7. Idempotency Tests
# ===========================================================================

class TestIdempotency:
    """Verify that re-running seed functions does not duplicate records."""

    def test_dealer_seed_idempotent(self, db_session: Session):
        """Running seed_dealers again should not add duplicate dealer rows."""
        from backend.app.database.seed_data import seed_dealers

        count_before = db_session.query(Dealer).count()
        seed_dealers(db_session)
        count_after = db_session.query(Dealer).count()
        assert count_before == count_after, (
            f"Dealer count changed from {count_before} to {count_after} after re-seed"
        )

    def test_customer_seed_idempotent(self, db_session: Session):
        """Running seed_customers again should not add duplicate customer rows."""
        import random
        from backend.app.database.seed_data import seed_customers

        count_before = db_session.query(Customer).count()
        seed_customers(db_session, random.Random(42), count=count_before)
        count_after = db_session.query(Customer).count()
        assert count_before == count_after, (
            f"Customer count changed from {count_before} to {count_after} after re-seed"
        )

    def test_vehicle_seed_idempotent(self, db_session: Session):
        """Running seed_vehicles again should not add duplicate vehicles."""
        import random
        from backend.app.database.seed_data import seed_vehicles

        customers = db_session.query(Customer).all()
        count_before = db_session.query(Vehicle).count()
        seed_vehicles(db_session, random.Random(42), customers)
        count_after = db_session.query(Vehicle).count()
        assert count_before == count_after, (
            f"Vehicle count changed from {count_before} to {count_after} after re-seed"
        )

    def test_transaction_seed_idempotent(self, db_session: Session):
        """Running seed_transactions again should not add duplicate transactions."""
        import random
        from backend.app.database.seed_data import seed_transactions

        customers = db_session.query(Customer).all()
        vehicles = db_session.query(Vehicle).all()
        dealers = db_session.query(Dealer).all()
        count_before = db_session.query(Transaction).count()
        seed_transactions(
            db_session, random.Random(42), customers, vehicles, dealers, target_count=count_before
        )
        count_after = db_session.query(Transaction).count()
        assert count_before == count_after, (
            f"Transaction count changed from {count_before} to {count_after} after re-seed"
        )

    def test_service_visit_seed_idempotent(self, db_session: Session):
        """Running seed_service_visits again should not add duplicate service visits."""
        import random
        from backend.app.database.seed_data import seed_service_visits

        vehicles = db_session.query(Vehicle).all()
        dealers = db_session.query(Dealer).all()
        count_before = db_session.query(ServiceVisit).count()
        seed_service_visits(
            db_session, random.Random(42), vehicles, dealers, target_count=count_before
        )
        count_after = db_session.query(ServiceVisit).count()
        assert count_before == count_after, (
            f"ServiceVisit count changed from {count_before} to {count_after} after re-seed"
        )

    def test_loyalty_event_seed_idempotent(self, db_session: Session):
        """Running seed_loyalty_events again should not add duplicate loyalty events."""
        import random
        from backend.app.database.seed_data import seed_loyalty_events

        customers = db_session.query(Customer).all()
        transactions = db_session.query(Transaction).all()
        count_before = db_session.query(LoyaltyEvent).count()
        seed_loyalty_events(
            db_session, random.Random(42), customers, transactions, target_count=count_before
        )
        count_after = db_session.query(LoyaltyEvent).count()
        assert count_before == count_after, (
            f"LoyaltyEvent count changed from {count_before} to {count_after} after re-seed"
        )

    def test_review_seed_idempotent(self, db_session: Session):
        """Running seed_reviews again should not add duplicate reviews."""
        import random
        from backend.app.database.seed_data import seed_reviews

        customers = db_session.query(Customer).all()
        dealers = db_session.query(Dealer).all()
        vehicles = db_session.query(Vehicle).all()
        count_before = db_session.query(CustomerReview).count()
        seed_reviews(
            db_session, random.Random(42), customers, dealers, vehicles, target_count=count_before
        )
        count_after = db_session.query(CustomerReview).count()
        assert count_before == count_after, (
            f"CustomerReview count changed from {count_before} to {count_after} after re-seed"
        )

    def test_full_seed_database_idempotent_isolated(self):
        """Running seed_database twice on a fresh isolated database produces identical counts."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend.app.database.base import Base
        from backend.app.database.seed_data import seed_database

        test_engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=test_engine)
        Session = sessionmaker(bind=test_engine)
        session = Session()

        try:
            # First seed run
            counts_run1 = seed_database(session)
            db_counts_run1 = {
                "dealers": session.query(Dealer).count(),
                "customers": session.query(Customer).count(),
                "vehicles": session.query(Vehicle).count(),
                "transactions": session.query(Transaction).count(),
                "service_visits": session.query(ServiceVisit).count(),
                "loyalty_events": session.query(LoyaltyEvent).count(),
                "customer_reviews": session.query(CustomerReview).count(),
            }
            assert counts_run1 == db_counts_run1

            # Second seed run
            counts_run2 = seed_database(session)
            db_counts_run2 = {
                "dealers": session.query(Dealer).count(),
                "customers": session.query(Customer).count(),
                "vehicles": session.query(Vehicle).count(),
                "transactions": session.query(Transaction).count(),
                "service_visits": session.query(ServiceVisit).count(),
                "loyalty_events": session.query(LoyaltyEvent).count(),
                "customer_reviews": session.query(CustomerReview).count(),
            }

            # Verify complete idempotency: every table count is unchanged
            assert counts_run2 == counts_run1
            assert db_counts_run2 == db_counts_run1

            # Verify expected target counts
            assert db_counts_run2["dealers"] == 5
            assert db_counts_run2["customers"] == 100
            assert db_counts_run2["vehicles"] == 161
            assert db_counts_run2["transactions"] == 400
            assert db_counts_run2["service_visits"] == 300
            assert db_counts_run2["loyalty_events"] == 413
            assert db_counts_run2["customer_reviews"] == 150
        finally:
            session.close()
            Base.metadata.drop_all(bind=test_engine)
            test_engine.dispose()
