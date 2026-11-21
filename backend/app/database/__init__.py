"""
AutoInsight360 - Database Package
==================================
Provides SQLAlchemy engine, session factory, and model base.
"""

from .connection import engine, SessionLocal, get_db
from .base import Base
from .models import Customer, Vehicle, Dealer, Transaction, ServiceVisit, LoyaltyEvent, CustomerReview

__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "Base",
    "Customer",
    "Vehicle",
    "Dealer",
    "Transaction",
    "ServiceVisit",
    "LoyaltyEvent",
    "CustomerReview",
]
