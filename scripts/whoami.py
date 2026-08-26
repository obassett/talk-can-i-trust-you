"""Slide 27 — 'get an identity, present no secret'.

Connects to the local Workload API socket, prints this workload's SPIFFE ID,
and shows the short-lived cert's serial + expiry (run it twice a few minutes
apart to watch the SVID rotate).

Run: python scripts/whoami.py
"""

from __future__ import annotations

import logging
import warnings

from spiffe import X509Source

# Keep live-demo output clean: hush py-spiffe's benign teardown log
# ("gRPC error: StatusCode.CANCELLED" when the source closes) and the
# X509Source.svid deprecation notice — the slide shows `source.svid`, so we keep it.
logging.getLogger("spiffe").setLevel(logging.CRITICAL)
warnings.filterwarnings("ignore", category=DeprecationWarning)


def main() -> None:
    # No key file, no token, no bootstrap secret. The agent attests *this*
    # process and hands back the identity it's entitled to.
    with X509Source(timeout_in_seconds=30) as source:
        svid = source.svid
        leaf = svid.cert_chain[0]
        print(f"SPIFFE ID : {svid.spiffe_id}")
        print(f"serial    : {hex(leaf.serial_number)}")
        print(f"expires   : {leaf.not_valid_after_utc}")
        print("note      : no secret was presented to obtain this identity")


if __name__ == "__main__":
    main()
