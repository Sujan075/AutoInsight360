"""
AutoInsight360 - Currency Policy & Standardisation Service
===========================================================
Defines the enterprise currency policy and formatting rules for AutoInsight360.

Enterprise Policy:
1. Operational & Reporting Currency: Indian Rupee (INR - ₹).
2. All customer-facing financial metrics (CLTV, service costs, parts, labour,
   vehicle prices, and transaction amounts) are presented in INR.
3. Approved Reference Conversion Rates (documented benchmark):
   - 1 USD = 84.00 INR (RBI benchmark reference rate for enterprise systems)
   - INR = 1.00 (Base)
4. Non-INR source transactions imported into AutoInsight360 are either
   explicitly converted using the approved benchmark reference rate or
   rejected with an actionable validation error if the currency is unsupported.
5. Legacy records lacking currency metadata are officially classified as INR.
"""

from __future__ import annotations

import decimal
from typing import Optional, Tuple

# Official enterprise base currency
ENTERPRISE_CURRENCY = "INR"
CURRENCY_SYMBOL = "₹"

# Approved documented benchmark conversion rate
APPROVED_USD_TO_INR_RATE = 84.00

# Supported transaction currencies for ingestion
SUPPORTED_CURRENCIES = {"INR", "USD"}


def format_inr(
    amount: Optional[float | int | decimal.Decimal],
    show_symbol: bool = True,
    decimals: int = 2,
) -> str:
    """
    Format a numeric amount according to the Indian numbering system:
    - Last 3 digits before decimal are grouped together, then subsequent digits in pairs.
    - Examples: 1,45,000.00; 450.00; 10,00,000.00.

    Parameters
    ----------
    amount : numeric or None
    show_symbol : bool, default True (prepends '₹')
    decimals : int, default 2

    Returns
    -------
    str : Formatted currency string
    """
    if amount is None:
        return f"{CURRENCY_SYMBOL}0.00" if show_symbol else "0.00"

    try:
        val = float(amount)
    except (ValueError, TypeError):
        return f"{CURRENCY_SYMBOL}0.00" if show_symbol else "0.00"

    is_negative = val < 0
    val = abs(val)

    # Format to fixed decimals
    fmt_str = f"{{:.{decimals}f}}"
    formatted_num = fmt_str.format(val)
    parts = formatted_num.split(".")
    int_part = parts[0]
    dec_part = f".{parts[1]}" if len(parts) > 1 else ""

    if len(int_part) <= 3:
        formatted_int = int_part
    else:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        # Group rest into pairs from right to left
        groups = []
        while len(rest) > 2:
            groups.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.insert(0, rest)
        formatted_int = ",".join(groups) + "," + last3

    symbol_str = f"{CURRENCY_SYMBOL}" if show_symbol else ""
    sign_str = "-" if is_negative else ""
    return f"{sign_str}{symbol_str}{formatted_int}{dec_part}"


def convert_to_inr(amount: float, source_currency: Optional[str] = "INR") -> Tuple[float, bool, str]:
    """
    Convert a transaction amount to INR using the approved enterprise conversion rate.

    Returns
    -------
    (amount_inr, was_converted, audit_note)
    """
    curr = (source_currency or "INR").strip().upper()

    if curr == "INR":
        return round(float(amount), 2), False, "Direct INR amount"

    if curr == "USD":
        converted = round(float(amount) * APPROVED_USD_TO_INR_RATE, 2)
        note = (
            f"Converted from ${amount:,.2f} USD to ₹{converted:,.2f} INR "
            f"using approved benchmark rate (1 USD = ₹{APPROVED_USD_TO_INR_RATE:.2f})"
        )
        return converted, True, note

    raise ValueError(
        f"Unsupported currency '{curr}'. AutoInsight360 standard currency is INR. "
        f"Supported source currencies: {', '.join(sorted(SUPPORTED_CURRENCIES))}."
    )


def validate_currency_code(currency: Optional[str]) -> bool:
    """Check if the provided currency string is supported under enterprise policy."""
    if not currency or not currency.strip():
        return True  # Defaults to INR
    return currency.strip().upper() in SUPPORTED_CURRENCIES
