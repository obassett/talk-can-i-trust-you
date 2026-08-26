"""Order Service business logic, kept pure so it's unit-testable without SPIRE.

The rule the whole talk hangs on: never dispatch a package unless payment was
taken. Round 1's incident was exactly this rule being unenforceable because
Dispatch couldn't tell who was calling.
"""

from __future__ import annotations

from .protocol import ShipRequest


class PaymentError(Exception):
    """Raised when payment could not be taken; we must not ship."""


def charge_card(package_id: str, amount_cents: int) -> bool:
    """Demo stub for a payment provider call.

    Returns True if the charge 'succeeds'. A real implementation would call
    Stripe/Adyen/etc. Here, any positive amount succeeds.
    """
    return amount_cents > 0


def build_ship_request(package_id: str, address: str, amount_cents: int) -> ShipRequest:
    """Charge the customer, then build the ship request marked `charged=True`.

    Raises PaymentError if the charge failed, so a shipment is never created
    for an unpaid order.
    """
    if not charge_card(package_id, amount_cents):
        raise PaymentError(f"payment failed for {package_id!r}; refusing to ship")
    return ShipRequest(package_id=package_id, address=address, charged=True)
