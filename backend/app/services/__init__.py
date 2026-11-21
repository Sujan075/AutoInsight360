"""
AutoInsight360 - Services Package
==================================
Business logic services for customer intelligence, metrics, and AI queries.
"""

from .customer_service import search_customers, get_customer_360, get_system_health

__all__ = [
    "search_customers",
    "get_customer_360",
    "get_system_health",
]
