"""
AutoInsight360 - Customer Schemas
==================================
Pydantic schemas for Customer 360 models, search results, and AI queries.
"""

from __future__ import annotations

import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Health Check Schema
# ---------------------------------------------------------------------------
class HealthCheckResponse(BaseModel):
    status: str
    database: str
    database_file: str
    total_customers: int
    total_vehicles: int
    total_dealers: int
    total_transactions: int
    total_services: int
    model_name: str
    model_available: bool


# ---------------------------------------------------------------------------
# Search / Summary Schema
# ---------------------------------------------------------------------------
class CustomerSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    customer_segment: Optional[str] = None
    is_active: bool
    loyalty_points: int
    vehicles_count: int
    primary_vehicle: Optional[str] = None


# ---------------------------------------------------------------------------
# Detail Schemas
# ---------------------------------------------------------------------------
class CustomerDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    full_name: str
    email: str
    phone: Optional[str] = None
    date_of_birth: Optional[datetime.date] = None
    gender: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: str = "USA"
    postal_code: Optional[str] = None
    customer_segment: Optional[str] = None
    preferred_contact: Optional[str] = None
    is_active: bool
    loyalty_points_balance: int
    registered_at: datetime.datetime
    updated_at: datetime.datetime


class VehicleDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    vin: str
    make: str
    model: str
    year: int
    color: Optional[str] = None
    trim: Optional[str] = None
    body_style: Optional[str] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    engine: Optional[str] = None
    purchase_date: Optional[datetime.date] = None
    purchase_price: Optional[float] = None
    mileage_at_purchase: Optional[int] = None
    current_mileage: Optional[int] = None
    is_primary: bool
    is_active: bool
    created_at: datetime.datetime
    service_visits_count: int = 0


class TransactionDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    dealer_id: int
    dealer_name: Optional[str] = None
    vehicle_id: Optional[int] = None
    vehicle_info: Optional[str] = None
    transaction_type: str
    amount: float
    currency: str = "USD"
    transaction_date: datetime.date
    payment_method: Optional[str] = None
    status: str
    reference_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime.datetime


class ServiceVisitDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vehicle_id: int
    vehicle_vin: Optional[str] = None
    vehicle_info: Optional[str] = None
    dealer_id: int
    dealer_name: Optional[str] = None
    service_type: str
    service_date: datetime.date
    mileage_at_service: Optional[int] = None
    cost: Optional[float] = None
    description: Optional[str] = None
    technician_notes: Optional[str] = None
    is_warranty: bool
    next_service_date: Optional[datetime.date] = None
    created_at: datetime.datetime


class LoyaltyEventDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    event_type: str
    points: int
    event_date: datetime.date
    description: Optional[str] = None
    related_transaction_id: Optional[int] = None
    related_transaction_ref: Optional[str] = None
    balance_after: int
    created_at: datetime.datetime


class CustomerReviewDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    dealer_id: Optional[int] = None
    dealer_name: Optional[str] = None
    vehicle_id: Optional[int] = None
    vehicle_info: Optional[str] = None
    review_type: str
    rating: int
    title: Optional[str] = None
    body: Optional[str] = None
    review_date: datetime.date
    is_verified: bool
    is_published: bool
    created_at: datetime.datetime


# ---------------------------------------------------------------------------
# Customer 360 Aggregated Metrics
# ---------------------------------------------------------------------------
class Customer360Metrics(BaseModel):
    cltv_total: float = 0.0
    cltv_vehicle_spend: float = 0.0
    cltv_service_spend: float = 0.0
    cltv_parts_accessories_spend: float = 0.0
    total_transactions_count: int = 0
    completed_transactions_count: int = 0
    total_vehicles_count: int = 0
    total_services_count: int = 0
    total_service_cost: float = 0.0
    loyalty_points_balance: int = 0
    loyalty_points_earned: int = 0
    loyalty_points_redeemed: int = 0
    total_reviews_count: int = 0
    average_rating: Optional[float] = None
    first_activity_date: Optional[datetime.date] = None
    last_activity_date: Optional[datetime.date] = None


# ---------------------------------------------------------------------------
# Complete Customer 360 Response
# ---------------------------------------------------------------------------
class Customer360Response(BaseModel):
    customer: CustomerDetail
    metrics: Customer360Metrics
    vehicles: List[VehicleDetail]
    transactions: List[TransactionDetail]
    service_visits: List[ServiceVisitDetail]
    loyalty_events: List[LoyaltyEventDetail]
    reviews: List[CustomerReviewDetail]


# ---------------------------------------------------------------------------
# Agent Request / Response
# ---------------------------------------------------------------------------
class AgentQueryRequest(BaseModel):
    customer_id: int = Field(..., gt=0, description="Valid Customer ID")
    question: str = Field(
        ...,
        min_length=3,
        max_length=500,
        description="Natural language question about the customer (3-500 chars)",
    )


class AgentQueryResponse(BaseModel):
    customer_id: int
    customer_name: str
    question: str
    answer: str
    evidence_records: List[str] = []
    model: str
    status: str
