"""
AutoInsight360 - Annual Loyalty Points Service
================================================
Implements the 2026 annual visit-based and birthday bonus loyalty policy.

Business Rules:
1. LOYALTY_PROGRAM_YEAR = 2026
2. Rule A (Visit-based points):
   - Only completed service visits dated within 2026 earn visit points (+100 pts).
   - Service visits in 2025 or earlier do NOT earn 2026 visit points.
   - Each qualifying service visit earns points exactly once (tracked via service_visit_id).
3. Rule B (Birthday bonus):
   - Customers receive a birthday bonus (+500 pts) once per program year.
   - Requires valid date_of_birth.
   - Future birthdays within the program year are not automatically awarded in advance.
4. Rule C (Annual balance):
   - 2026 Balance = 2026 Visit Points + 2026 Birthday Points - 2026 Redeemed Points.
   - Previous year historical events are excluded from the 2026 balance.
5. Redemption:
   - Rejects non-positive amounts and over-redemption beyond available 2026 balance.
   - Records redemption on the loyalty ledger and updates customer balance.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.app.database.models import Customer, LoyaltyEvent, ServiceVisit, Vehicle

logger = logging.getLogger(__name__)

# Configurable prototype demo policy values
LOYALTY_PROGRAM_YEAR: int = 2026
POINTS_PER_COMPLETED_VISIT: int = 100
BIRTHDAY_BONUS_POINTS: int = 500

DEFAULT_REFERENCE_DATE = datetime.date(2026, 11, 21)


def get_program_reference_date() -> datetime.date:
    """Return the effective system reference date for 2026 loyalty operations."""
    return DEFAULT_REFERENCE_DATE


def calculate_birthday_in_year(dob: datetime.date, year: int) -> datetime.date:
    """Calculate the customer's birthday for a given year, handling leap years."""
    try:
        return datetime.date(year, dob.month, dob.day)
    except ValueError:
        # Handles Feb 29 birthday on a non-leap year
        return datetime.date(year, 2, 28)


def get_annual_loyalty_summary(
    db: Session,
    customer_id: int,
    year: int = LOYALTY_PROGRAM_YEAR,
) -> Dict[str, Any]:
    """
    Compute the current-year loyalty metrics and ledger items for a customer.
    Excludes past-year activity from the current-year balance.
    """
    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise ValueError(f"Customer #{customer_id} does not exist.")

    # All loyalty events for customer
    all_events = (
        db.query(LoyaltyEvent)
        .filter(LoyaltyEvent.customer_id == customer_id)
        .order_by(LoyaltyEvent.event_date.desc(), LoyaltyEvent.id.desc())
        .all()
    )

    # Filter events belonging to the program year
    year_events: List[LoyaltyEvent] = []
    historical_events: List[LoyaltyEvent] = []

    for ev in all_events:
        # Check explicit program_year or event_date.year
        ev_year = ev.program_year if ev.program_year is not None else ev.event_date.year
        if ev_year == year:
            year_events.append(ev)
        else:
            historical_events.append(ev)

    # Break down 2026 points
    visit_points = 0
    birthday_points = 0
    other_earned = 0
    redeemed_points = 0

    has_birthday_bonus = False
    qualifying_visits_rewarded = set()

    for ev in year_events:
        etype = ev.event_type.lower()
        if ev.points > 0:
            if "birthday" in etype or "birthday" in (ev.description or "").lower():
                birthday_points += ev.points
                has_birthday_bonus = True
            elif "visit" in etype or ev.service_visit_id is not None or "visit" in (ev.description or "").lower():
                visit_points += ev.points
                if ev.service_visit_id:
                    qualifying_visits_rewarded.add(ev.service_visit_id)
            else:
                other_earned += ev.points
        else:
            redeemed_points += abs(ev.points)

    total_earned_2026 = visit_points + birthday_points + other_earned
    annual_balance_2026 = max(0, total_earned_2026 - redeemed_points)

    # Lifetime balance across all years
    total_lifetime_earned = sum(ev.points for ev in all_events if ev.points > 0)
    total_lifetime_redeemed = abs(sum(ev.points for ev in all_events if ev.points < 0))
    lifetime_balance = max(0, total_lifetime_earned - total_lifetime_redeemed) if all_events else customer.loyalty_points_balance

    return {
        "customer_id": customer_id,
        "program_year": year,
        "annual_balance": annual_balance_2026,
        "visit_points_earned": visit_points,
        "birthday_points_earned": birthday_points,
        "other_points_earned": other_earned,
        "total_earned_year": total_earned_2026,
        "redeemed_points_year": redeemed_points,
        "has_birthday_bonus": has_birthday_bonus,
        "qualifying_visits_count": len(qualifying_visits_rewarded),
        "rewarded_service_visit_ids": list(qualifying_visits_rewarded),
        "lifetime_balance": lifetime_balance,
        "year_events": year_events,
        "historical_events": historical_events,
    }


def reconcile_loyalty_rewards(
    db: Session,
    customer_id: Optional[int] = None,
    reference_date: Optional[datetime.date] = None,
) -> Dict[str, Any]:
    """
    Evaluate and award 2026 visit-based rewards and birthday bonuses.
    Safe to execute repeatedly; guaranteed idempotent.

    Parameters
    ----------
    db : Session
    customer_id : int, optional (reconciles single customer or all customers)
    reference_date : datetime.date, optional (defaults to 2026-11-21)

    Returns
    -------
    dict with counts of visit rewards and birthday bonuses awarded.
    """
    ref_date = reference_date or get_program_reference_date()
    target_year = LOYALTY_PROGRAM_YEAR

    # Resolve customers to process
    if customer_id:
        customers = db.query(Customer).filter(Customer.id == customer_id).all()
    else:
        customers = db.query(Customer).all()

    visit_rewards_awarded = 0
    birthday_bonuses_awarded = 0

    for customer in customers:
        # 1. Existing rewarded service visit IDs for this customer
        existing_rewarded_sv_ids = {
            ev.service_visit_id
            for ev in db.query(LoyaltyEvent.service_visit_id)
            .filter(
                LoyaltyEvent.customer_id == customer.id,
                LoyaltyEvent.service_visit_id.isnot(None),
            )
            .all()
            if ev[0] is not None
        }

        # 2. Check completed 2026 service visits for customer's vehicles
        customer_vehicle_ids = [
            v.id for v in db.query(Vehicle.id).filter(Vehicle.customer_id == customer.id).all()
        ]

        if customer_vehicle_ids:
            qualifying_visits = (
                db.query(ServiceVisit)
                .filter(
                    ServiceVisit.vehicle_id.in_(customer_vehicle_ids),
                    ServiceVisit.service_date >= datetime.date(target_year, 1, 1),
                    ServiceVisit.service_date <= datetime.date(target_year, 12, 31),
                )
                .all()
            )

            for sv in qualifying_visits:
                # Must be completed status (default completed if None)
                status = (sv.service_status or "completed").lower()
                if status not in ("completed", "done", "closed"):
                    continue

                if sv.id not in existing_rewarded_sv_ids:
                    # Award visit reward
                    new_event = LoyaltyEvent(
                        customer_id=customer.id,
                        event_type="visit_reward",
                        points=POINTS_PER_COMPLETED_VISIT,
                        event_date=sv.service_date,
                        service_visit_id=sv.id,
                        program_year=target_year,
                        description=(
                            f"2026 Service Visit Reward - {sv.service_type.replace('_', ' ').title()} "
                            f"(Visit #{sv.id})"
                        ),
                        balance_after=customer.loyalty_points_balance + POINTS_PER_COMPLETED_VISIT,
                    )
                    customer.loyalty_points_balance += POINTS_PER_COMPLETED_VISIT
                    db.add(new_event)
                    existing_rewarded_sv_ids.add(sv.id)
                    visit_rewards_awarded += 1
                    logger.info(
                        "Awarded %d visit points to Customer #%d for Service Visit #%d",
                        POINTS_PER_COMPLETED_VISIT,
                        customer.id,
                        sv.id,
                    )

        # 3. Check Birthday Bonus
        if customer.date_of_birth:
            # Check if birthday bonus already awarded for target year
            already_awarded_birthday = (
                db.query(LoyaltyEvent)
                .filter(
                    LoyaltyEvent.customer_id == customer.id,
                    LoyaltyEvent.program_year == target_year,
                    LoyaltyEvent.event_type.in_(["birthday_bonus", "BIRTHDAY_BONUS"]),
                )
                .first()
                is not None
            )

            if not already_awarded_birthday:
                bday_this_year = calculate_birthday_in_year(customer.date_of_birth, target_year)
                # Only award if birthday has occurred on or before reference date (not in future)
                if bday_this_year <= ref_date:
                    bday_event = LoyaltyEvent(
                        customer_id=customer.id,
                        event_type="birthday_bonus",
                        points=BIRTHDAY_BONUS_POINTS,
                        event_date=bday_this_year,
                        program_year=target_year,
                        description=f"{target_year} Birthday Bonus Reward ({customer.first_name})",
                        balance_after=customer.loyalty_points_balance + BIRTHDAY_BONUS_POINTS,
                    )
                    customer.loyalty_points_balance += BIRTHDAY_BONUS_POINTS
                    db.add(bday_event)
                    birthday_bonuses_awarded += 1
                    logger.info(
                        "Awarded %d birthday bonus points to Customer #%d (%s) for year %d",
                        BIRTHDAY_BONUS_POINTS,
                        customer.id,
                        customer.first_name,
                        target_year,
                    )

    if visit_rewards_awarded > 0 or birthday_bonuses_awarded > 0:
        db.flush()
        db.commit()

    return {
        "status": "success",
        "program_year": target_year,
        "visit_rewards_awarded": visit_rewards_awarded,
        "birthday_bonuses_awarded": birthday_bonuses_awarded,
        "customers_evaluated": len(customers),
    }


def redeem_loyalty_points(
    db: Session,
    customer_id: int,
    amount: int,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Redeem loyalty points for a customer against their 2026 annual balance.

    Validates:
    - Amount > 0
    - Amount <= Available 2026 Balance

    Atomic commit with ledger entry.
    """
    if amount <= 0:
        raise ValueError(f"Redemption amount must be greater than zero. Received: {amount}")

    customer = db.query(Customer).filter(Customer.id == customer_id).first()
    if not customer:
        raise ValueError(f"Customer #{customer_id} does not exist.")

    summary = get_annual_loyalty_summary(db, customer_id, LOYALTY_PROGRAM_YEAR)
    available_2026 = summary["annual_balance"]

    if amount > available_2026:
        raise ValueError(
            f"Redemption amount ({amount:,} pts) exceeds available {LOYALTY_PROGRAM_YEAR} "
            f"loyalty balance ({available_2026:,} pts)."
        )

    # Execute redemption
    new_balance = max(0, customer.loyalty_points_balance - amount)
    customer.loyalty_points_balance = new_balance

    redemption_event = LoyaltyEvent(
        customer_id=customer.id,
        event_type="redeem",
        points=-amount,
        event_date=get_program_reference_date(),
        program_year=LOYALTY_PROGRAM_YEAR,
        description=f"{LOYALTY_PROGRAM_YEAR} Loyalty Redemption - {notes or 'Customer Rewards'}",
        balance_after=new_balance,
    )
    db.add(redemption_event)

    db.flush()
    db.commit()

    logger.info("Customer #%d successfully redeemed %d loyalty points.", customer_id, amount)

    updated_summary = get_annual_loyalty_summary(db, customer_id, LOYALTY_PROGRAM_YEAR)

    return {
        "status": "success",
        "customer_id": customer.id,
        "redeemed_amount": amount,
        "remaining_2026_balance": updated_summary["annual_balance"],
        "lifetime_balance": updated_summary["lifetime_balance"],
        "event_id": redemption_event.id,
        "message": f"Successfully redeemed {amount:,} points. Available 2026 balance: {updated_summary['annual_balance']:,} pts.",
    }
