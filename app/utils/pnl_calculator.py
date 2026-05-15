"""
Pure P/L calculation functions.
These are the single source of truth for all profit/loss math.
"""
from decimal import Decimal, ROUND_HALF_UP


def calculate_pnl(
    direction: str,
    entry_price: Decimal,
    exit_price: Decimal,
    quantity: Decimal,
    fees: Decimal = Decimal("0"),
) -> Decimal:
    """
    Calculate P/L for a trade.

    LONG:  P/L = (exit - entry) * qty - fees
    SHORT: P/L = (entry - exit) * qty - fees
    """
    if direction.upper() == "LONG":
        raw_pnl = (exit_price - entry_price) * quantity
    elif direction.upper() == "SHORT":
        raw_pnl = (entry_price - exit_price) * quantity
    else:
        raise ValueError(f"Invalid direction: {direction}. Must be LONG or SHORT.")

    return (raw_pnl - fees).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def calculate_pnl_percent(
    pnl: Decimal,
    entry_price: Decimal,
    quantity: Decimal,
) -> Decimal:
    """
    Calculate P/L as a percentage of invested capital.
    P/L% = (P/L / (entry_price * quantity)) * 100
    """
    invested = entry_price * quantity
    if invested == 0:
        return Decimal("0")
    return (pnl / invested * 100).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def classify_result(pnl: Decimal) -> str:
    """Classify a trade as WIN, LOSS, or BREAKEVEN."""
    if pnl > 0:
        return "WIN"
    elif pnl < 0:
        return "LOSS"
    return "BREAKEVEN"
