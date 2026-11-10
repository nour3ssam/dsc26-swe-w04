import pytest
from nour_transfers.rules import can_transfer, days_of_cover, priority

# --- Public Example Tests ---
def test_reserve_is_kept_exactly():
    assert can_transfer(from_stock=40, quantity=30, reserve=10) is True


def test_no_sales_means_no_urgency():
    assert days_of_cover(stock=12, avg_daily_sales=0) is None
    assert priority(is_chronic=True, cover_days=None) == "normal"


# --- Mutant Killers ---
class TestDaysOfCoverMutants:
    def test_normal_calculation(self):
        assert days_of_cover(10, 2) == 5.0

    def test_zero_sales_returns_none(self):
        # Kills M05: no sales treated as zero cover (returns 0.0 instead of None)
        assert days_of_cover(10, 0) is None

    def test_negative_stock_raises_value_error(self):
        with pytest.raises(ValueError):
            days_of_cover(-1, 2)

    def test_negative_sales_raises_value_error(self):
        with pytest.raises(ValueError):
            days_of_cover(10, -2)


class TestPriorityMutants:
    def test_none_cover_returns_normal(self):
        assert priority(is_chronic=True, cover_days=None) == "normal"
        assert priority(is_chronic=False, cover_days=None) == "normal"

    def test_urgent_chronic_under_3_days(self):
        assert priority(is_chronic=True, cover_days=2.9) == "urgent"

    def test_urgent_boundary_exactly_3_days(self):
        # Kills M04: cover of exactly 3 days becomes urgent
        assert priority(is_chronic=True, cover_days=3.0) == "high"

    def test_non_chronic_low_cover_is_not_urgent(self):
        # Kills M03: non-chronic items with low cover become urgent
        assert priority(is_chronic=False, cover_days=1.0) == "high"

    def test_high_priority_under_7_days(self):
        assert priority(is_chronic=False, cover_days=6.9) == "high"
        assert priority(is_chronic=True, cover_days=5.0) == "high"

    def test_normal_priority_7_days_or_more(self):
        assert priority(is_chronic=True, cover_days=7.0) == "normal"
        assert priority(is_chronic=False, cover_days=10.0) == "normal"


class TestCanTransferMutants:
    def test_can_transfer_success(self):
        assert can_transfer(from_stock=10, quantity=5, reserve=3) is True

    def test_reserve_exact_boundary(self):
        # Kills M01: reserve boundary off by one (>= becomes >)
        assert can_transfer(from_stock=10, quantity=7, reserve=3) is True

    def test_below_reserve_fails(self):
        assert can_transfer(from_stock=10, quantity=8, reserve=3) is False

    def test_zero_quantity_disallowed(self):
        # Kills M02: zero quantity allowed
        assert can_transfer(from_stock=10, quantity=0, reserve=3) is False

    def test_negative_quantity_disallowed(self):
        assert can_transfer(from_stock=10, quantity=-1, reserve=3) is False