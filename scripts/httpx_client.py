"""Slide 30 — dropping SPIFFE into httpx.

REFERENCE SNIPPET. Dispatch in this repo speaks a raw mTLS socket protocol
(see services/dispatch), not HTTPS, so this script is here to show the
*pattern* for talking to a SPIFFE-mTLS *HTTP* service. Point it at any
HTTPS endpoint inside your trust domain.

`SpiffeSSLContext` is a stdlib-compatible SSL context that refreshes the SVID
as it rotates, so long-running clients keep working without re-creating it.
"""

from __future__ import annotations

import httpx
from spiffe import X509Source
from spiffetls import SpiffeSSLContext


def main() -> None:
    source = X509Source(timeout_in_seconds=30)

    # In-mesh: trust only the SPIFFE bundle. Add use_system_trusted_cas=True
    # only when the endpoint also legitimately presents a publicly-trusted cert.
    ssl_context = SpiffeSSLContext(source)

    client = httpx.Client(verify=ssl_context)
    resp = client.get("https://dispatch.prod:8443/health")
    print(resp.status_code, resp.text)


if __name__ == "__main__":
    main()
