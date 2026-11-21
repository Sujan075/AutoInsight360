"""
AutoInsight360 - Phase 2.2 Annual Loyalty Points Tests
=======================================================
Tests the 2026 annual visit-based rewards, birthday bonus, balance calculation,
reconciliation idempotency, and controlled points redemption.
"""

import datetime
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.database.connection import SessionLocal
from backend.app.database.models import Customer, Dealer, LoyaltyEvent, ServiceVisit, Vehicle
from backend.app.main import app
from backend.app.services.loyalty_service import (
    BIRTHDAY_BONUS_POINTS,
    LOYALTY_PROGRAM_YEAR,
    POINTS_PER_COMPLETED_VISIT,
    get_annual_loyalty_summary,
    reconcile_loyalty_rewards,
    redeem_loyalty_points,
)

client = TestClient(app)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_completed_2026_service_visit_earns_visit_points(db: Session):
    """Completed service visit in 2026 earns exactly 100 visit points."""
    uid = uuid.uuid4().hex[:6]
    dealer = Dealer(name=f"Loyalty DLR {uid}", city="Dallas", state="TX")
    customer = Customer(first_name="Rohan", last_name="Sharma", email=f"rohan_{uid}@autoinsight.demo")
    db.add_all([dealer, customer])
    db.flush()

    vehicle = Vehicle(customer_id=customer.id, vin=f"SYNTH-LOY-{uid}".upper(), make="Hyundai", model="Ioniq 5", year=2024)
    db.add(vehicle)
    db.flush()

    # 2026 Completed visit
    visit_2026 = ServiceVisit(
        vehicle_id=vehicle.id,
        dealer_id=dealer.id,
        service_type="oil_change",
        service_date=datetime.date(2026, 3, 10),
        service_status="completed",
        cost=4500.00,
    )
    db.add(visit_2026)
    db.flush()

    # Reconcile
    rec = reconcile_loyalty_rewards(db, customer_id=customer.id)
    assert rec["visit_rewards_awarded"] >= 1

    summary = get_annual_loyalty_summary(db, customer.id, 2026)
    assert summary["visit_points_earned"] == POINTS_PER_COMPLETED_VISIT
    assert summary["annual_balance"] == POINTS_PER_COMPLETED_VISIT


def test_service_visit_in_2025_does_not_earn_2026_points(db: Session):
    """A service visit from 2025 or earlier must NOT generate 2026 visit points."""
    uid = uuid.uuid4().hex[:6]
    dealer = Dealer(name=f"Past DLR {uid}", city="Austin", state="TX")
    customer = Customer(first_name="Priya", last_name="Nair", email=f"priya_{uid}@autoinsight.demo")
    db.add_all([dealer, customer])
    db.flush()

    vehicle = Vehicle(customer_id=customer.id, vin=f"SYNTH-PST-{uid}".upper(), make="Kia", model="EV6", year=2023)
    db.add(vehicle)
    db.flush()

    # 2025 Completed visit
    visit_2025 = ServiceVisit(
        vehicle_id=vehicle.id,
        dealer_id=dealer.id,
        service_type="oil_change",
        service_date=datetime.date(2025, 11, 20),
        service_status="completed",
        cost=3800.00,
    )
    db.add(visit_2025)
    db.flush()

    # Reconcile for 2026
    rec = reconcile_loyalty_rewards(db, customer_id=customer.id)
    summary = get_annual_loyalty_summary(db, customer.id, 2026)

    assert summary["visit_points_earned"] == 0
    assert summary["annual_balance"] == 0


def test_birthday_bonus_awarded_once_in_program_year(db: Session):
    """Customer with valid DOB whose birthday occurred in 2026 receives birthday bonus once."""
    uid = uuid.uuid4().hex[:6]
    customer = Customer(
        first_name="Vikram",
        last_name="Mehta",
        email=f"vikram_{uid}@autoinsight.demo",
        date_of_birth=datetime.date(1992, 4, 15),  # Birthday occurred in April (before Nov 21)
    )
    db.add(customer)
    db.flush()

    reconcile_loyalty_rewards(db, customer_id=customer.id)
    summary = get_annual_loyalty_summary(db, customer.id, 2026)

    assert summary["has_birthday_bonus"] is True
    assert summary["birthday_points_earned"] == BIRTHDAY_BONUS_POINTS
    assert summary["annual_balance"] == BIRTHDAY_BONUS_POINTS

    # Re-run reconciliation (idempotency check)
    rec2 = reconcile_loyalty_rewards(db, customer_id=customer.id)
    assert rec2["birthday_bonuses_awarded"] == 0

    summary2 = get_annual_loyalty_summary(db, customer.id, 2026)
    assert summary2["birthday_points_earned"] == BIRTHDAY_BONUS_POINTS


def test_missing_date_of_birth_does_not_create_birthday_bonus(db: Session):
    """Customer with no date_of_birth must NOT receive a birthday bonus."""
    uid = uuid.uuid4().hex[:6]
    customer = Customer(
        first_name="NoDob",
        last_name="User",
        email=f"nodob_{uid}@autoinsight.demo",
        date_of_birth=None,
    )
    db.add(customer)
    db.flush()

    reconcile_loyalty_rewards(db, customer_id=customer.id)
    summary = get_annual_loyalty_summary(db, customer.id, 2026)

    assert summary["has_birthday_bonus"] is False
    assert summary["birthday_points_earned"] == 0


def test_future_birthday_not_automatically_awarded(db: Session):
    """Customer whose birthday is in December 2026 (after Nov 21 reference date) is not awarded in advance."""
    uid = uuid.uuid4().hex[:6]
    customer = Customer(
        first_name="FutureBday",
        last_name="User",
        email=f"future_{uid}@autoinsight.demo",
        date_of_birth=datetime.date(1995, 12, 25),  # Dec 25 is after Nov 21
    )
    db.add(customer)
    db.flush()

    reconcile_loyalty_rewards(db, customer_id=customer.id, reference_date=datetime.date(2026, 11, 21))
    summary = get_annual_loyalty_summary(db, customer.id, 2026)

    assert summary["has_birthday_bonus"] is False
    assert summary["birthday_points_earned"] == 0


def test_annual_balance_excludes_previous_years(db: Session):
    """Historical loyalty events from 2023-2025 are excluded from 2026 annual balance."""
    uid = uuid.uuid4().hex[:6]
    customer = Customer(
        first_name="Ananya",
        last_name="Sen",
        email=f"ananya_{uid}@autoinsight.demo",
    )
    db.add(customer)
    db.flush()

    # Past events from 2024
    past_event1 = LoyaltyEvent(
        customer_id=customer.id,
        event_type="earn",
        points=400,
        event_date=datetime.date(2024, 5, 10),
        program_year=2024,
        description="2024 Earn",
    )
    # Event in 2026
    event_2026 = LoyaltyEvent(
        customer_id=customer.id,
        event_type="visit_reward",
        points=100,
        event_date=datetime.date(2026, 6, 15),
        program_year=2026,
        description="2026 Visit",
    )
    db.add_all([past_event1, event_2026])
    db.flush()
    db.commit()

    summary = get_annual_loyalty_summary(db, customer.id, 2026)
    assert summary["annual_balance"] == 100
    assert summary["lifetime_balance"] == 500


def test_redeem_loyalty_points_via_api(db: Session):
    """Test point redemption via POST /api/customers/{id}/loyalty/redeem."""
    uid = uuid.uuid4().hex[:6]
    customer = Customer(
        first_name="RedeemTest",
        last_name="User",
        email=f"redeem_{uid}@autoinsight.demo",
        date_of_birth=datetime.date(1989, 2, 10),  # Eligible for 500 bday pts
    )
    db.add(customer)
    db.flush()

    # Award birthday bonus (500 pts)
    reconcile_loyalty_rewards(db, customer_id=customer.id)

    # Redeem 200 points
    resp = client.post(
        f"/api/customers/{customer.id}/loyalty/redeem",
        json={"amount": 200, "notes": "Oil Change Discount Voucher"},
    )
    assert resp.status_code == 200
    rdata = resp.json()
    assert rdata["status"] == "success"
    assert rdata["redeemed_amount"] == 200
    assert rdata["remaining_2026_balance"] == 300

    # Over-redemption must be rejected
    over_resp = client.post(
        f"/api/customers/{customer.id}/loyalty/redeem",
        json={"amount": 500, "notes": "Excessive redemption"},
    )
    assert over_resp.status_code == 400
    assert "exceeds available 2026 loyalty balance" in over_resp.json()["detail"]


def test_redeem_non_positive_points_rejected():
    """Redemption with zero or negative points must return 400 Bad Request."""
    resp1 = client.post("/api/customers/1/loyalty/redeem", json={"amount": 0})
    assert resp1.status_code == 422 or resp1.status_code == 400

    resp2 = client.post("/api/customers/1/loyalty/redeem", json={"amount": -50})
    assert resp2.status_code == 422 or resp2.status_code == 400
