"""Omen tries to make Dispatch ship a free Xbox. This should FAIL.

Run this from a workload whose identity is NOT the Order Service (e.g. register
this as spiffe://acme.internal/ns/prod/sa/omen and run it there). Two ways it
can fail, both good:

  * If Omen has *some* valid SVID that isn't order-service, Dispatch's
    authorize_id(ORDER_ID) rejects the handshake — a valid cert is not enough.
  * If Omen has no registered identity at all, X509Source can't even obtain an
    SVID, so there's nothing to present.

Either way: Omen doesn't stand a chance.

Run: python scripts/omen.py
"""

from __future__ import annotations

import logging
import warnings

from spiffe import X509Source
from spiffetls import dial
from spiffetls.tlsconfig.authorize import authorize_id

# Keep the live payoff clean: hush py-spiffe's benign teardown log
# ("gRPC error: StatusCode.CANCELLED") and the X509Source.svid deprecation notice.
logging.getLogger("spiffe").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=DeprecationWarning)

from spiffe_demo.config import DISPATCH_ADDR, DISPATCH_ID
from spiffe_demo.protocol import ShipRequest, decode_response, encode_request
from spiffe_demo.sslio import recv_line, send_all


def main() -> None:
    try:
        source = X509Source(timeout_in_seconds=30)
    except Exception as e:
        print(f"[omen] couldn't even get an identity: {type(e).__name__}: {e}")
        print("[omen] no registered identity → nothing to present. Blocked.")
        return

    print(f"[omen] my identity is: {source.svid.spiffe_id}  (NOT order-service)")

    # Note: charged=False — Omen never pays.
    req = ShipRequest(package_id="xbox-series-x", address="Omen's lair", charged=False)

    try:
        conn = dial(DISPATCH_ADDR, source, authorize_fn=authorize_id(DISPATCH_ID))
        conn.setblocking(True)
        send_all(conn, encode_request(req))
        resp = decode_response(recv_line(conn))
        print(f"[omen] response: {resp}")
        print("[omen] uh oh — that should NOT have worked.")
    except Exception as e:
        print(f"[omen] REJECTED by Dispatch: {type(e).__name__}: {e}")
        print("[omen] Dispatch refused because my SPIFFE ID isn't order-service.")
    finally:
        source.close()


if __name__ == "__main__":
    main()
