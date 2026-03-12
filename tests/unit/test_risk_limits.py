from decimal import Decimal

from trading_system.risk.limits import RiskLimits


def test_allows_order_within_limits() -> None:
    limits = RiskLimits(
        max_position=Decimal("1.0"),
        max_notional=Decimal("100000"),
        max_order_size=Decimal("0.25"),
    )

    allowed = limits.allows_order(
        current_position=Decimal("0.10"),
        order_size=Decimal("0.20"),
        price=Decimal("50000"),
    )

    assert allowed is True


def test_rejects_order_when_size_exceeds_limit() -> None:
    limits = RiskLimits(
        max_position=Decimal("1.0"),
        max_notional=Decimal("100000"),
        max_order_size=Decimal("0.25"),
    )

    allowed = limits.allows_order(
        current_position=Decimal("0.10"),
        order_size=Decimal("0.30"),
        price=Decimal("50000"),
    )

    assert allowed is False
