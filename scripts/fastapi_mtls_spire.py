"""Run / call the FastAPI SPIFFE-mTLS listener against the REAL Workload API.

Meant to run INSIDE a container that has the SPIRE agent socket. Two roles:

  serve  — start the FastAPI listener; identity comes from this workload's SVID.
  call   — make an mTLS request to it; identity comes from this workload's SVID.

The response echoes BOTH SPIFFE IDs — the server's and the caller's — so one
call shows both ends of the mutually-authenticated connection. Example (via just
fastapi-demo): server runs in the dispatch container, client calls from order:

    { "status": "SHIPPED",
      "server_spiffe_id": "spiffe://acme.internal/ns/prod/sa/dispatch-service",
      "client_spiffe_id": "spiffe://acme.internal/ns/prod/sa/order-service" }
"""

from __future__ import annotations

import argparse
import json
import logging
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import httpx
import uvicorn
from spiffe import X509Source
from spiffetls import SpiffeSSLContext

from spiffe_demo.fastapi_mtls import SpiffePeerProtocol, create_app, write_ssl_material

# The spiffe logger emits a benign "X509 Source Error: ... CANCELLED" when the
# source's Workload API stream is torn down at exit — quiet it so the demo output
# stays clean. (Not a deprecation; there's no call to fix, it's a shutdown race.)
logging.getLogger("spiffe").setLevel(logging.CRITICAL)


def cmd_serve(args: argparse.Namespace) -> int:
    source = X509Source(timeout_in_seconds=30)
    me = str(source.get_x509_context().default_svid.spiffe_id)
    allowed = args.authorize or [me]
    print(f"[serve] my SPIFFE ID   = {me}", flush=True)
    print(f"[serve] will authorize = {', '.join(allowed)}", flush=True)
    app = create_app(authorized=allowed, server_id=me)
    with TemporaryDirectory() as d:
        ssl_kwargs = write_ssl_material(source, Path(d))
        try:
            uvicorn.run(
                app, host=args.host, port=args.port, http=SpiffePeerProtocol,
                log_level="warning", **ssl_kwargs,
            )
        finally:
            source.close()
    return 0


def cmd_call(args: argparse.Namespace) -> int:
    source = X509Source(timeout_in_seconds=30)
    me = str(source.get_x509_context().default_svid.spiffe_id)
    print(f"[call] my SPIFFE ID = {me}", flush=True)
    # SpiffeSSLContext presents our SVID as the client cert and verifies the
    # server's cert against the trust bundle — no hostname check (SPIFFE certs
    # carry a URI SAN, not a DNS name).
    ctx = SpiffeSSLContext(source)
    try:
        with httpx.Client(verify=ctx) as client:
            resp = client.post(args.url, json={"package_id": "pkg-1", "address": "1 Main St"})
        print(f"[call] POST {args.url} -> {resp.status_code}", flush=True)
        print(json.dumps(resp.json(), indent=2), flush=True)
        return 0 if resp.status_code == 200 else 1
    finally:
        source.close()


def cmd_selfcall(args: argparse.Namespace) -> int:
    """Convenience: serve in a background thread and call ourselves once.

    Server and client share this workload's identity, so both SPIFFE IDs match —
    handy on a single container to prove the wiring end to end.
    """
    source = X509Source(timeout_in_seconds=30)
    me = str(source.get_x509_context().default_svid.spiffe_id)
    print(f"[selfcall] my SPIFFE ID = {me}", flush=True)
    app = create_app(authorized=[me], server_id=me)
    with TemporaryDirectory() as d:
        ssl_kwargs = write_ssl_material(source, Path(d))
        config = uvicorn.Config(
            app, host="127.0.0.1", port=args.port, http=SpiffePeerProtocol,
            log_level="warning", **ssl_kwargs,
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()
        while not server.started:
            time.sleep(0.05)
        ctx = SpiffeSSLContext(source)
        with httpx.Client(verify=ctx) as client:
            resp = client.post(
                f"https://127.0.0.1:{args.port}/ship",
                json={"package_id": "pkg-1", "address": "1 Main St"},
            )
        print(f"[selfcall] POST /ship -> {resp.status_code}", flush=True)
        print(json.dumps(resp.json(), indent=2), flush=True)
        server.should_exit = True
        thread.join(timeout=5)
    source.close()
    return 0 if resp.status_code == 200 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_serve = sub.add_parser("serve", help="run the FastAPI mTLS listener")
    p_serve.add_argument("--host", default="0.0.0.0")
    p_serve.add_argument("--port", type=int, default=8443)
    p_serve.add_argument("--authorize", action="append", help="SPIFFE ID(s) allowed to /ship")
    p_serve.set_defaults(func=cmd_serve)

    p_call = sub.add_parser("call", help="make an mTLS request to the listener")
    p_call.add_argument("--url", default="https://dispatch:8443/ship")
    p_call.set_defaults(func=cmd_call)

    p_self = sub.add_parser("selfcall", help="serve + call in one process (same identity)")
    p_self.add_argument("--port", type=int, default=8443)
    p_self.set_defaults(func=cmd_selfcall)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
