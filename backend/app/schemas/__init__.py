"""
AutoInsight360 - Schemas Package
=================================
Pydantic models for API request and response validation.
"""

from .customer_schemas import (
    CustomerSummaryResponse,
    CustomerDetail,
    VehicleDetail,
    TransactionDetail,
    ServiceVisitDetail,
    LoyaltyEventDetail,
    CustomerReviewDetail,
    Customer360Metrics,
    Customer360Response,
    AgentQueryRequest,
    AgentQueryResponse,
    HealthCheckResponse,
)

__all__ = [
    "CustomerSummaryResponse",
    "CustomerDetail",
    "VehicleDetail",
    "TransactionDetail",
    "ServiceVisitDetail",
    "LoyaltyEventDetail",
    "CustomerReviewDetail",
    "Customer360Metrics",
    "Customer360Response",
    "AgentQueryRequest",
    "AgentQueryResponse",
    "HealthCheckResponse",
]
