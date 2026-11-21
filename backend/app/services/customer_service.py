"""
AutoInsight360 - Customer Service
===================================
Database querying, Customer 360 profile aggregation, and CLTV calculations.
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from backend.app.database.connection import get_database_path
from backend.app.database.models import (
    Customer,
    CustomerReview,
    Dealer,
    LoyaltyEvent,
    ServiceVisit,
    Transaction,
    Vehicle,
)
from backend.app.schemas.customer_schemas import (
    Customer360Metrics,
    Customer360Response,
    CustomerDetail,
    CustomerReviewDetail,
    CustomerSummaryResponse,
    HealthCheckResponse,
    LoyaltyEventDetail,
    ServiceVisitDetail,
    TransactionDetail,
    VehicleDetail,
)


def get_system_health(db: Session, model_available: bool = False, model_name: str = "llama3.1:latest") -> HealthCheckResponse:
    """Return health metrics and row counts from the connected database."""
    return HealthCheckResponse(
        status="healthy",
        database="connected",
        database_file=str(get_database_path()),
        total_customers=db.query(Customer).count(),
        total_vehicles=db.query(Vehicle).count(),
        total_dealers=db.query(Dealer).count(),
        total_transactions=db.query(Transaction).count(),
        total_services=db.query(ServiceVisit).count(),
        model_name=model_name,
        model_available=model_available,
    )


def search_customers(
    db: Session,
    query: Optional[str] = None,
    limit: int = 20,
) -> List[CustomerSummaryResponse]:
    """
    Search customers by ID, first name, last name, full name, email, phone, or VIN.

    If query is empty or None, returns top customers ordered by ID.
    """
    base_query = db.query(Customer)

    if query and query.strip():
        q = query.strip()
        conditions = []

        # 1. Exact numeric ID search
        if q.isdigit():
            conditions.append(Customer.id == int(q))

        # 2. Name search (first, last, or combined)
        pattern = f"%{q}%"
        conditions.append(Customer.first_name.ilike(pattern))
        conditions.append(Customer.last_name.ilike(pattern))
        conditions.append(Customer.email.ilike(pattern))
        conditions.append(Customer.phone.ilike(pattern))
        conditions.append(Customer.city.ilike(pattern))

        # 3. Search by VIN in vehicles owned by customer
        matching_customer_ids_by_vin = (
            db.query(Vehicle.customer_id)
            .filter(Vehicle.vin.ilike(pattern))
            .scalar_subquery()
        )
        conditions.append(Customer.id.in_(matching_customer_ids_by_vin))

        base_query = base_query.filter(or_(*conditions))

    customers = (
        base_query.order_by(Customer.id)
        .limit(min(max(limit, 1), 100))
        .all()
    )

    results: List[CustomerSummaryResponse] = []
    for c in customers:
        vehicles = c.vehicles
        primary = next((v for v in vehicles if v.is_primary), vehicles[0] if vehicles else None)
        primary_str = f"{primary.year} {primary.make} {primary.model}" if primary else None

        results.append(
            CustomerSummaryResponse(
                id=c.id,
                first_name=c.first_name,
                last_name=c.last_name,
                full_name=f"{c.first_name} {c.last_name}",
                email=c.email,
                phone=c.phone,
                city=c.city,
                state=c.state,
                customer_segment=c.customer_segment,
                is_active=c.is_active,
                loyalty_points=c.loyalty_points_balance,
                vehicles_count=len(vehicles),
                primary_vehicle=primary_str,
            )
        )

    return results


def get_customer_360(db: Session, customer_id: int) -> Optional[Customer360Response]:
    """
    Retrieve the complete Customer 360 profile for a customer.

    Aggregates:
    - Customer demographic and profile details
    - Customer-owned vehicles with service counts
    - Full financial transaction history with dealer names
    - Complete service visits across all vehicles with dealer and vehicle info
    - Loyalty events history and calculated balance
    - Customer reviews and feedback
    - Calculated Customer Lifetime Value (CLTV) metrics
    """
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id)
        .first()
    )
    if not customer:
        return None

    # 1. Vehicles
    vehicles_db = (
        db.query(Vehicle)
        .filter(Vehicle.customer_id == customer_id)
        .order_by(Vehicle.is_primary.desc(), Vehicle.year.desc())
        .all()
    )
    vehicle_map = {v.id: v for v in vehicles_db}

    # 2. Dealers lookup map
    dealers_db = db.query(Dealer).all()
    dealer_map = {d.id: d.name for d in dealers_db}

    # 3. Transactions
    transactions_db = (
        db.query(Transaction)
        .filter(Transaction.customer_id == customer_id)
        .order_by(Transaction.transaction_date.desc(), Transaction.id.desc())
        .all()
    )

    # 4. Service Visits (linked via customer vehicles)
    vehicle_ids = [v.id for v in vehicles_db]
    if vehicle_ids:
        service_visits_db = (
            db.query(ServiceVisit)
            .filter(ServiceVisit.vehicle_id.in_(vehicle_ids))
            .order_by(ServiceVisit.service_date.desc(), ServiceVisit.id.desc())
            .all()
        )
    else:
        service_visits_db = []

    # Map service counts per vehicle
    vehicle_service_counts: dict[int, int] = {}
    for sv in service_visits_db:
        vehicle_service_counts[sv.vehicle_id] = vehicle_service_counts.get(sv.vehicle_id, 0) + 1

    # 5. Loyalty Events
    loyalty_events_db = (
        db.query(LoyaltyEvent)
        .filter(LoyaltyEvent.customer_id == customer_id)
        .order_by(LoyaltyEvent.event_date.desc(), LoyaltyEvent.id.desc())
        .all()
    )

    # Map transaction reference numbers
    tx_ref_map = {t.id: t.reference_number for t in transactions_db}

    # 6. Customer Reviews
    reviews_db = (
        db.query(CustomerReview)
        .filter(CustomerReview.customer_id == customer_id)
        .order_by(CustomerReview.review_date.desc(), CustomerReview.id.desc())
        .all()
    )

    # -----------------------------------------------------------------------
    # Calculate Customer 360 Metrics & Historical CLTV
    # -----------------------------------------------------------------------
    completed_txs = [t for t in transactions_db if t.status == "completed"]
    cltv_total = sum(float(t.amount) for t in completed_txs)
    cltv_vehicle = sum(float(t.amount) for t in completed_txs if t.transaction_type == "vehicle_purchase")
    cltv_service = sum(float(t.amount) for t in completed_txs if t.transaction_type == "service_payment")
    cltv_parts_acc = sum(
        float(t.amount) for t in completed_txs if t.transaction_type in ("parts", "accessories")
    )

    total_service_cost = sum(float(sv.cost) for sv in service_visits_db if sv.cost is not None)

    loyalty_earned = sum(le.points for le in loyalty_events_db if le.points > 0)
    loyalty_redeemed = abs(sum(le.points for le in loyalty_events_db if le.points < 0))
    calculated_loyalty_balance = (loyalty_earned - loyalty_redeemed) if loyalty_events_db else customer.loyalty_points_balance

    avg_rating = (
        round(sum(r.rating for r in reviews_db) / len(reviews_db), 1)
        if reviews_db
        else None
    )

    # Activity dates
    all_dates: list[datetime.date] = []
    all_dates.extend(t.transaction_date for t in transactions_db)
    all_dates.extend(sv.service_date for sv in service_visits_db)
    all_dates.extend(r.review_date for r in reviews_db)
    all_dates.extend(le.event_date for le in loyalty_events_db)

    first_activity = min(all_dates) if all_dates else None
    last_activity = max(all_dates) if all_dates else None

    metrics = Customer360Metrics(
        cltv_total=round(cltv_total, 2),
        cltv_vehicle_spend=round(cltv_vehicle, 2),
        cltv_service_spend=round(cltv_service, 2),
        cltv_parts_accessories_spend=round(cltv_parts_acc, 2),
        total_transactions_count=len(transactions_db),
        completed_transactions_count=len(completed_txs),
        total_vehicles_count=len(vehicles_db),
        total_services_count=len(service_visits_db),
        total_service_cost=round(total_service_cost, 2),
        loyalty_points_balance=max(0, calculated_loyalty_balance),
        loyalty_points_earned=loyalty_earned,
        loyalty_points_redeemed=loyalty_redeemed,
        total_reviews_count=len(reviews_db),
        average_rating=avg_rating,
        first_activity_date=first_activity,
        last_activity_date=last_activity,
    )

    # -----------------------------------------------------------------------
    # Format Response Lists
    # -----------------------------------------------------------------------
    customer_detail = CustomerDetail(
        id=customer.id,
        first_name=customer.first_name,
        last_name=customer.last_name,
        full_name=f"{customer.first_name} {customer.last_name}",
        email=customer.email,
        phone=customer.phone,
        date_of_birth=customer.date_of_birth,
        gender=customer.gender,
        city=customer.city,
        state=customer.state,
        country=customer.country,
        postal_code=customer.postal_code,
        customer_segment=customer.customer_segment,
        preferred_contact=customer.preferred_contact,
        is_active=customer.is_active,
        loyalty_points_balance=customer.loyalty_points_balance,
        registered_at=customer.registered_at,
        updated_at=customer.updated_at,
    )

    vehicles_detail: List[VehicleDetail] = []
    for v in vehicles_db:
        vehicles_detail.append(
            VehicleDetail(
                id=v.id,
                customer_id=v.customer_id,
                vin=v.vin,
                make=v.make,
                model=v.model,
                year=v.year,
                color=v.color,
                trim=v.trim,
                body_style=v.body_style,
                fuel_type=v.fuel_type,
                transmission=v.transmission,
                engine=v.engine,
                purchase_date=v.purchase_date,
                purchase_price=float(v.purchase_price) if v.purchase_price is not None else None,
                mileage_at_purchase=v.mileage_at_purchase,
                current_mileage=v.current_mileage,
                is_primary=v.is_primary,
                is_active=v.is_active,
                created_at=v.created_at,
                service_visits_count=vehicle_service_counts.get(v.id, 0),
            )
        )

    transactions_detail: List[TransactionDetail] = []
    for t in transactions_db:
        v = vehicle_map.get(t.vehicle_id) if t.vehicle_id else None
        v_info = f"{v.year} {v.make} {v.model}" if v else None
        transactions_detail.append(
            TransactionDetail(
                id=t.id,
                customer_id=t.customer_id,
                dealer_id=t.dealer_id,
                dealer_name=dealer_map.get(t.dealer_id, "Unknown Dealer"),
                vehicle_id=t.vehicle_id,
                vehicle_info=v_info,
                transaction_type=t.transaction_type,
                amount=float(t.amount),
                currency=t.currency,
                transaction_date=t.transaction_date,
                payment_method=t.payment_method,
                status=t.status,
                reference_number=t.reference_number,
                notes=t.notes,
                created_at=t.created_at,
            )
        )

    service_visits_detail: List[ServiceVisitDetail] = []
    for sv in service_visits_db:
        v = vehicle_map.get(sv.vehicle_id)
        service_visits_detail.append(
            ServiceVisitDetail(
                id=sv.id,
                vehicle_id=sv.vehicle_id,
                vehicle_vin=v.vin if v else None,
                vehicle_info=f"{v.year} {v.make} {v.model}" if v else None,
                dealer_id=sv.dealer_id,
                dealer_name=dealer_map.get(sv.dealer_id, "Unknown Dealer"),
                service_type=sv.service_type,
                service_date=sv.service_date,
                mileage_at_service=sv.mileage_at_service,
                cost=float(sv.cost) if sv.cost is not None else None,
                description=sv.description,
                technician_notes=sv.technician_notes,
                is_warranty=sv.is_warranty,
                next_service_date=sv.next_service_date,
                created_at=sv.created_at,
            )
        )

    loyalty_events_detail: List[LoyaltyEventDetail] = []
    for le in loyalty_events_db:
        loyalty_events_detail.append(
            LoyaltyEventDetail(
                id=le.id,
                customer_id=le.customer_id,
                event_type=le.event_type,
                points=le.points,
                event_date=le.event_date,
                description=le.description,
                related_transaction_id=le.related_transaction_id,
                related_transaction_ref=tx_ref_map.get(le.related_transaction_id),
                balance_after=le.balance_after,
                created_at=le.created_at,
            )
        )

    reviews_detail: List[CustomerReviewDetail] = []
    for r in reviews_db:
        v = vehicle_map.get(r.vehicle_id) if r.vehicle_id else None
        reviews_detail.append(
            CustomerReviewDetail(
                id=r.id,
                customer_id=r.customer_id,
                dealer_id=r.dealer_id,
                dealer_name=dealer_map.get(r.dealer_id) if r.dealer_id else None,
                vehicle_id=r.vehicle_id,
                vehicle_info=f"{v.year} {v.make} {v.model}" if v else None,
                review_type=r.review_type,
                rating=r.rating,
                title=r.title,
                body=r.body,
                review_date=r.review_date,
                is_verified=r.is_verified,
                is_published=r.is_published,
                created_at=r.created_at,
            )
        )

    return Customer360Response(
        customer=customer_detail,
        metrics=metrics,
        vehicles=vehicles_detail,
        transactions=transactions_detail,
        service_visits=service_visits_detail,
        loyalty_events=loyalty_events_detail,
        reviews=reviews_detail,
    )
