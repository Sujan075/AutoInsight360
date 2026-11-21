"""
AutoInsight360 - ORM Models
=============================
Defines the full relational schema for the automotive customer
intelligence database.

Tables
------
dealers          - Automotive dealerships
customers        - Individual customer profiles
vehicles         - Customer-owned vehicles
transactions     - Purchase/financial transactions at a dealer
service_visits   - Scheduled maintenance and repair records
loyalty_events   - Points earned or redeemed per customer
customer_reviews - Customer-submitted feedback

Relationships
-------------
- Customer 1──* Vehicle        (a customer may own many vehicles)
- Customer 1──* Transaction    (a customer may have many transactions)
- Customer 1──* LoyaltyEvent   (a customer may have many loyalty events)
- Customer 1──* CustomerReview (a customer may submit many reviews)
- Vehicle  1──* ServiceVisit   (a vehicle may have many service visits)
- Vehicle  1──* Transaction    (a vehicle may appear on many transactions)
- Dealer   1──* Transaction    (a dealer handles many transactions)
- Dealer   1──* ServiceVisit   (a dealer performs many service visits)

Naming conventions
------------------
- Table names: snake_case, plural
- Column names: snake_case
- Primary keys: id (integer, auto-increment)
- Foreign keys: <table_singular>_id
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


# ---------------------------------------------------------------------------
# Helper: current UTC timestamp
# ---------------------------------------------------------------------------
def _utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.UTC)


# ===========================================================================
# Dealer
# ===========================================================================
class Dealer(Base):
    """
    Represents an automotive dealership.

    A dealer is associated with transactions and service visits.
    Dealers are seeded once and referenced by ID throughout the data.
    """

    __tablename__ = "dealers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    city: Mapped[str] = mapped_column(String(80), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="USA")
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # Relationships
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="dealer", lazy="select"
    )
    service_visits: Mapped[List["ServiceVisit"]] = relationship(
        "ServiceVisit", back_populates="dealer", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Dealer id={self.id} name={self.name!r}>"


# ===========================================================================
# Customer
# ===========================================================================
class Customer(Base):
    """
    Represents an automotive customer (individual person).

    Synthetic data note: all names, emails, phones and addresses
    in this table are entirely fictitious and generated for
    demonstration purposes only.
    """

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # -- Identification (synthetic only) ------------------------------------
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    # Synthetic email: format demo_<id>@autoinsight.demo to avoid real addresses
    email: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # -- Demographics -------------------------------------------------------
    date_of_birth: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    gender: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # -- Address (synthetic) ------------------------------------------------
    city: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    country: Mapped[str] = mapped_column(String(50), nullable=False, default="USA")
    postal_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # -- Customer profile ---------------------------------------------------
    customer_segment: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # e.g. Premium, Standard, Fleet
    preferred_contact: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # email | phone | sms
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # -- Loyalty summary (denormalised for quick lookup) --------------------
    loyalty_points_balance: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )

    # -- Timestamps ---------------------------------------------------------
    registered_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    # -- Relationships ------------------------------------------------------
    vehicles: Mapped[List["Vehicle"]] = relationship(
        "Vehicle", back_populates="owner", lazy="select", cascade="all, delete-orphan"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="customer", lazy="select"
    )
    loyalty_events: Mapped[List["LoyaltyEvent"]] = relationship(
        "LoyaltyEvent", back_populates="customer", lazy="select", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["CustomerReview"]] = relationship(
        "CustomerReview", back_populates="customer", lazy="select", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_customers_email", "email"),
        Index("ix_customers_last_name", "last_name"),
    )

    def __repr__(self) -> str:
        return f"<Customer id={self.id} name={self.first_name!r} {self.last_name!r}>"


# ===========================================================================
# Vehicle
# ===========================================================================
class Vehicle(Base):
    """
    Represents a vehicle owned by a customer.

    VINs in this dataset are synthetic and not real vehicle identifiers.
    They are prefixed with 'SYNTH-' to make this unambiguous.
    """

    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )

    # -- Vehicle identity ---------------------------------------------------
    vin: Mapped[str] = mapped_column(String(30), nullable=False, unique=True)
    make: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g. Toyota
    model: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. Camry
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    color: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    trim: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    body_style: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    fuel_type: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    transmission: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    engine: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # -- Acquisition --------------------------------------------------------
    purchase_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    purchase_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    mileage_at_purchase: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    current_mileage: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # -- Status -------------------------------------------------------------
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # -- Timestamps ---------------------------------------------------------
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # -- Relationships ------------------------------------------------------
    owner: Mapped["Customer"] = relationship("Customer", back_populates="vehicles")
    service_visits: Mapped[List["ServiceVisit"]] = relationship(
        "ServiceVisit", back_populates="vehicle", lazy="select"
    )
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction", back_populates="vehicle", lazy="select"
    )

    __table_args__ = (
        CheckConstraint("year >= 1900 AND year <= 2100", name="ck_vehicle_year"),
        Index("ix_vehicles_customer_id", "customer_id"),
        Index("ix_vehicles_vin", "vin"),
    )

    def __repr__(self) -> str:
        return f"<Vehicle id={self.id} {self.year} {self.make} {self.model} VIN={self.vin!r}>"


# ===========================================================================
# Transaction
# ===========================================================================
class Transaction(Base):
    """
    Represents a financial transaction between a customer and a dealer.

    Transaction types include vehicle purchase, parts, accessories,
    service payments, etc.
    """

    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    dealer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dealers.id", ondelete="RESTRICT"), nullable=False
    )
    vehicle_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True
    )

    # -- Transaction details ------------------------------------------------
    transaction_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # vehicle_purchase | service_payment | parts | accessories | financing
    amount: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False, default="USD")
    transaction_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[Optional[str]] = mapped_column(
        String(30), nullable=True
    )  # cash | card | finance | lease
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="completed"
    )  # completed | refunded | pending | cancelled
    reference_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, unique=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # -- Timestamps ---------------------------------------------------------
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # -- Relationships ------------------------------------------------------
    customer: Mapped["Customer"] = relationship("Customer", back_populates="transactions")
    dealer: Mapped["Dealer"] = relationship("Dealer", back_populates="transactions")
    vehicle: Mapped[Optional["Vehicle"]] = relationship("Vehicle", back_populates="transactions")

    __table_args__ = (
        CheckConstraint("amount >= 0", name="ck_transaction_amount_positive"),
        Index("ix_transactions_customer_id", "customer_id"),
        Index("ix_transactions_dealer_id", "dealer_id"),
        Index("ix_transactions_date", "transaction_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} customer_id={self.customer_id} "
            f"type={self.transaction_type!r} amount={self.amount}>"
        )


# ===========================================================================
# ServiceVisit
# ===========================================================================
class ServiceVisit(Base):
    """
    Represents a single service visit for a vehicle at a dealer.

    Records maintenance, repairs and inspections.
    """

    __tablename__ = "service_visits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=False
    )
    dealer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("dealers.id", ondelete="RESTRICT"), nullable=False
    )

    # -- Visit details -------------------------------------------------------
    service_type: Mapped[str] = mapped_column(
        String(80), nullable=False
    )  # oil_change | tyre_rotation | brake_inspection | major_service | recall | warranty | repair
    service_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    mileage_at_service: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    technician_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_warranty: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    next_service_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)

    # -- Timestamps ---------------------------------------------------------
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # -- Relationships ------------------------------------------------------
    vehicle: Mapped["Vehicle"] = relationship("Vehicle", back_populates="service_visits")
    dealer: Mapped["Dealer"] = relationship("Dealer", back_populates="service_visits")

    __table_args__ = (
        CheckConstraint("cost >= 0", name="ck_service_cost_positive"),
        Index("ix_service_visits_vehicle_id", "vehicle_id"),
        Index("ix_service_visits_dealer_id", "dealer_id"),
        Index("ix_service_visits_date", "service_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<ServiceVisit id={self.id} vehicle_id={self.vehicle_id} "
            f"type={self.service_type!r} date={self.service_date}>"
        )


# ===========================================================================
# LoyaltyEvent
# ===========================================================================
class LoyaltyEvent(Base):
    """
    Records a single loyalty points event (earn or redeem) for a customer.

    The running balance is maintained on the Customer record.
    Each event stores the delta so the history is auditable.
    """

    __tablename__ = "loyalty_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )

    # -- Event details -------------------------------------------------------
    event_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # earn | redeem | adjustment | expiry | bonus
    points: Mapped[int] = mapped_column(
        Integer, nullable=False
    )  # positive = earn, negative = redeem/expiry
    event_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    related_transaction_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True
    )
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # -- Timestamps ---------------------------------------------------------
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # -- Relationships ------------------------------------------------------
    customer: Mapped["Customer"] = relationship("Customer", back_populates="loyalty_events")

    __table_args__ = (
        Index("ix_loyalty_events_customer_id", "customer_id"),
        Index("ix_loyalty_events_date", "event_date"),
    )

    def __repr__(self) -> str:
        return (
            f"<LoyaltyEvent id={self.id} customer_id={self.customer_id} "
            f"type={self.event_type!r} points={self.points}>"
        )


# ===========================================================================
# CustomerReview
# ===========================================================================
class CustomerReview(Base):
    """
    Records a customer-submitted review or feedback.

    Reviews may be for a dealer, a vehicle, or a service visit.
    Rating is 1–5 stars.
    """

    __tablename__ = "customer_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    customer_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("customers.id", ondelete="CASCADE"), nullable=False
    )
    dealer_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("dealers.id", ondelete="SET NULL"), nullable=True
    )
    vehicle_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("vehicles.id", ondelete="SET NULL"), nullable=True
    )

    # -- Review details -----------------------------------------------------
    review_type: Mapped[str] = mapped_column(
        String(30), nullable=False
    )  # dealer | vehicle | service
    rating: Mapped[int] = mapped_column(Integer, nullable=False)   # 1–5
    title: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    review_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_published: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # -- Timestamps ---------------------------------------------------------
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )

    # -- Relationships ------------------------------------------------------
    customer: Mapped["Customer"] = relationship("Customer", back_populates="reviews")

    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 5", name="ck_review_rating"),
        Index("ix_customer_reviews_customer_id", "customer_id"),
        Index("ix_customer_reviews_dealer_id", "dealer_id"),
    )

    def __repr__(self) -> str:
        return (
            f"<CustomerReview id={self.id} customer_id={self.customer_id} "
            f"rating={self.rating} type={self.review_type!r}>"
        )
