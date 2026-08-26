import pytest

from spiffe_demo.orders import PaymentError, build_ship_request, charge_card


def test_charge_succeeds_for_positive_amount():
    assert charge_card("pkg-1", 4999) is True


def test_charge_fails_for_zero_amount():
    assert charge_card("pkg-1", 0) is False


def test_build_ship_request_marks_charged():
    req = build_ship_request("pkg-1", "1 Main St", 4999)
    assert req.charged is True
    assert req.package_id == "pkg-1"
    assert req.address == "1 Main St"


def test_build_ship_request_refuses_when_unpaid():
    # No charge, no shipment — the rule Round 1 couldn't enforce.
    with pytest.raises(PaymentError):
        build_ship_request("xbox", "Omen's lair", 0)
