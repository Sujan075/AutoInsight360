"""
AutoInsight360 - Phase 2.2 Currency Standardisation Tests
==========================================================
Tests formatting, conversion, and validation of Indian Rupees (INR - ₹).
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.currency_service import (
    APPROVED_USD_TO_INR_RATE,
    CURRENCY_SYMBOL,
    convert_to_inr,
    format_inr,
    validate_currency_code,
)

client = TestClient(app)


def test_format_inr_basic():
    """Verify standard Indian numbering formatting."""
    assert format_inr(0) == "₹0.00"
    assert format_inr(450) == "₹450.00"
    assert format_inr(1200) == "₹1,200.00"
    assert format_inr(145000) == "₹1,45,000.00"
    assert format_inr(3850000) == "₹38,50,000.00"


def test_format_inr_large_and_negative():
    """Verify large crores/lakhs and negative amounts."""
    assert format_inr(10000000) == "₹1,00,00,000.00"
    assert format_inr(-4500) == "-₹4,500.00"
    assert format_inr(-145000) == "-₹1,45,000.00"
    assert format_inr(None) == "₹0.00"


def test_format_inr_without_symbol():
    """Verify formatting without currency symbol prefix."""
    assert format_inr(145000, show_symbol=False) == "1,45,000.00"
    assert format_inr(450.5, show_symbol=False) == "450.50"


def test_convert_to_inr_direct_inr():
    """Transactions in INR remain identical without conversion flags."""
    amount, was_converted, note = convert_to_inr(25000.00, "INR")
    assert amount == 25000.00
    assert was_converted is False
    assert "Direct INR" in note


def test_convert_to_inr_usd_benchmark():
    """Transactions in USD convert using the approved benchmark rate."""
    amount, was_converted, note = convert_to_inr(100.00, "USD")
    expected = round(100.00 * APPROVED_USD_TO_INR_RATE, 2)
    assert amount == expected
    assert was_converted is True
    assert "Converted from $100.00 USD" in note
    assert f"₹{APPROVED_USD_TO_INR_RATE:.2f}" in note


def test_convert_to_inr_unsupported_currency():
    """Unsupported foreign currencies raise ValueError."""
    with pytest.raises(ValueError, match="Unsupported currency 'EUR'"):
        convert_to_inr(500.00, "EUR")

    with pytest.raises(ValueError, match="Unsupported currency 'GBP'"):
        convert_to_inr(200.00, "GBP")


def test_validate_currency_code():
    """Verify currency code validation helper."""
    assert validate_currency_code("INR") is True
    assert validate_currency_code("inr") is True
    assert validate_currency_code("USD") is True
    assert validate_currency_code("") is True
    assert validate_currency_code("EUR") is False
    assert validate_currency_code("JPY") is False


def test_customer_360_api_returns_inr_currency():
    """Verify that GET /api/customers/{id}/360 returns INR currency metadata."""
    resp = client.get("/api/customers/1/360")
    assert resp.status_code == 200
    data = resp.json()

    assert data["metrics"]["currency"] == "INR"
    assert data["metrics"]["cltv_total"] >= 0

    # Transactions should specify currency
    if data["transactions"]:
        first_tx = data["transactions"][0]
        assert "currency" in first_tx
        assert "amount" in first_tx
