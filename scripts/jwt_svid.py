"""Slide 31 — reaching beyond the cluster with a JWT-SVID.

When you can't do end-to-end mTLS (an L7 proxy terminates TLS, or you're
calling an external partner), fetch a short-lived, audience-scoped JWT-SVID.
The token only validates against the audience you asked for.

Run: python scripts/jwt_svid.py
"""

from __future__ import annotations

import logging

from spiffe import JwtSource

# Keep live-demo output clean: hush py-spiffe's benign teardown log
# ("gRPC error: StatusCode.CANCELLED" when the source closes).
logging.getLogger("spiffe").setLevel(logging.CRITICAL)

AUDIENCE = {"https://partner.example.com"}


def main() -> None:
    with JwtSource(timeout_in_seconds=30) as source:
        svid = source.fetch_svid(audience=AUDIENCE)
        print(f"SPIFFE ID : {svid.spiffe_id}")
        print(f"audience  : {svid.audience}")
        print(f"expiry    : {svid.expiry}")
        # In a real call: headers={"Authorization": f"Bearer {svid.token}"}
        print(f"token     : {svid.token[:48]}...")


if __name__ == "__main__":
    main()
