"""Who is who, and where Dispatch lives.

The two SPIFFE IDs below are the entire authorization model of the demo:
Dispatch will only accept calls from ORDER_ID, and Order will only talk to a
server that proves it is DISPATCH_ID. Everything else — Omen included — is
refused at the TLS layer.
"""

from __future__ import annotations

import os

from spiffe import SpiffeId, TrustDomain

# The "realm". Every workload identity below lives inside it.
TRUST_DOMAIN = TrustDomain("acme.internal")


def workload_id(namespace: str, service_account: str) -> SpiffeId:
    """Build a SPIFFE ID using the SPIRE Kubernetes convention.

    e.g. spiffe://acme.internal/ns/prod/sa/order-service
    """
    return SpiffeId(f"spiffe://{TRUST_DOMAIN.name}/ns/{namespace}/sa/{service_account}")


ORDER_ID = workload_id("prod", "order-service")
DISPATCH_ID = workload_id("prod", "dispatch-service")

# Where Dispatch listens, and where Order dials. Overridable via env so the
# same code works on a laptop (127.0.0.1) and in docker-compose (service DNS).
DISPATCH_HOST = os.environ.get("DISPATCH_HOST", "127.0.0.1")
DISPATCH_PORT = int(os.environ.get("DISPATCH_PORT", "8443"))

# Server binds all interfaces; client dials the resolvable host.
DISPATCH_LISTEN = f"0.0.0.0:{DISPATCH_PORT}"
DISPATCH_ADDR = f"{DISPATCH_HOST}:{DISPATCH_PORT}"

# The Workload API socket. The SPIFFE libraries read SPIFFE_ENDPOINT_SOCKET
# from the environment automatically; this is only here for documentation and
# for scripts that want to print it.
WORKLOAD_API_SOCKET = os.environ.get(
    "SPIFFE_ENDPOINT_SOCKET", "unix:///run/spire/sockets/api.sock"
)
