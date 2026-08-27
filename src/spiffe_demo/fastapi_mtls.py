"""A FastAPI listener that speaks SPIFFE mTLS — and lets the **spiffe package**
do the identity validation, then hands the caller's SPIFFE ID to your handlers.

The raw ``spiffetls.listen`` server (services/dispatch/main.py) is the 20-line
mTLS primitive. This module is the *framework-native* counterpart: a normal
FastAPI app, served by uvicorn, wired so that

  * the server presents its SVID and the SPIFFE **trust bundle** is what verifies
    the client's certificate chain (real mTLS), and
  * the client's SPIFFE ID is authorized by ``spiffetls``'s own
    ``authorize_id`` — the exact same authorizer the raw Dispatch server uses —
    then handed to handlers via the ``caller_spiffe_id`` dependency.

Why it's split across two layers (and not pure spiffetls):

  * uvicorn runs on asyncio, whose TLS transport needs a standard-library
    ``ssl.SSLContext``. ``spiffetls`` builds a *pyOpenSSL* context (great for
    sync sockets / httpx) that asyncio can't drive. So we let uvicorn terminate
    TLS from the SVID + trust bundle (this does the chain validation SPIFFE
    requires), and we run ``spiffetls``' SPIFFE-ID authorization one layer up in
    a dependency. Same two checks spiffetls does in its verify callback
    (chain-to-bundle, then authorize the leaf's SPIFFE ID) — just at the app
    layer, so an unauthorized-but-valid cert gets a clean 403 instead of a
    handshake abort.
"""

from __future__ import annotations

import ssl
import tempfile
from pathlib import Path
from typing import Callable

import uvicorn
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding
from fastapi import Depends, FastAPI, HTTPException, Request
from OpenSSL import crypto
from pydantic import BaseModel
from spiffe import SpiffeId, X509Source
from spiffetls.tlsconfig.authorize import _spiffe_id_from_cert, authorize_one_of
from uvicorn.protocols.http.h11_impl import H11Protocol

_STATE_KEY = "peer_cert_der"


class SpiffePeerProtocol(H11Protocol):
    """uvicorn HTTP protocol that captures the client's certificate.

    asyncio calls ``connection_made`` only after the TLS handshake completes, so
    the peer certificate is available here. We stash its DER bytes in a
    per-connection copy of the ASGI ``state`` dict; the dependencies below turn
    that into a validated, authorized SPIFFE ID.
    """

    def connection_made(self, transport) -> None:  # type: ignore[override]
        super().connection_made(transport)
        der: bytes | None = None
        ssl_object = transport.get_extra_info("ssl_object")
        if ssl_object is not None:
            der = ssl_object.getpeercert(binary_form=True) or None
        # Per-connection state (a fresh dict on this instance; the shared
        # app_state is untouched). Surfaces to handlers via request.scope["state"].
        self.app_state = {**self.app_state, _STATE_KEY: der}


def _peer_cert(request: Request) -> crypto.X509 | None:
    """The client's leaf cert as a pyOpenSSL X509 — what spiffetls authorizers eat."""
    der = request.scope.get("state", {}).get(_STATE_KEY)
    if not der:
        return None
    return crypto.X509.from_cryptography(x509.load_der_x509_certificate(der))


def caller_spiffe_id(request: Request) -> SpiffeId:
    """FastAPI dependency: the caller's SPIFFE ID, extracted by the spiffe package.

    ``_spiffe_id_from_cert`` is spiffetls' own SAN→SpiffeId extractor (the one its
    authorizers use). No verified cert → 403 (an anonymous client never gets here,
    since mTLS is required at the handshake).
    """
    cert = _peer_cert(request)
    if cert is None:
        raise HTTPException(status_code=403, detail="no client certificate presented")
    return _spiffe_id_from_cert(cert)


def require_caller(*allowed: str) -> Callable[..., SpiffeId]:
    """Dependency factory enforcing ``spiffetls.authorize_one_of`` — the app-layer
    twin of the ``authorize_id`` line in services/dispatch/main.py."""
    authorizer = authorize_one_of({SpiffeId(s) for s in allowed})

    def dependency(request: Request) -> SpiffeId:
        cert = _peer_cert(request)
        if cert is None:
            raise HTTPException(status_code=403, detail="no client certificate presented")
        if not authorizer(cert):  # spiffe package validates the identity here
            raise HTTPException(
                status_code=403, detail=f"caller {_spiffe_id_from_cert(cert)} is not authorized"
            )
        return _spiffe_id_from_cert(cert)

    return dependency


class ShipRequest(BaseModel):
    package_id: str
    address: str


def create_app(*, authorized: list[str], server_id: str) -> FastAPI:
    """A tiny Dispatch-style app: only ``authorized`` SPIFFE IDs may ship.

    Every response echoes both SPIFFE IDs — the server's own (``server_id``, from
    its SVID) and the authenticated caller's — so a single call shows both ends of
    the mutually-authenticated identity.
    """
    app = FastAPI(title="Dispatch — FastAPI + SPIFFE mTLS")
    only = require_caller(*authorized)

    @app.get("/whoami")
    def whoami(caller: SpiffeId = Depends(caller_spiffe_id)) -> dict:
        return {"server_spiffe_id": server_id, "client_spiffe_id": str(caller)}

    @app.post("/ship")
    def ship(order: ShipRequest, caller: SpiffeId = Depends(only)) -> dict:
        return {
            "status": "SHIPPED",
            "package_id": order.package_id,
            "server_spiffe_id": server_id,
            "client_spiffe_id": str(caller),
        }

    return app


def write_ssl_material(source: X509Source, directory: Path) -> dict:
    """Write the current SVID + trust bundle to PEM and return uvicorn ssl_* kwargs.

    ``ssl_ca_certs`` = the SPIFFE trust bundle, so OpenSSL validates that the
    client's cert chains to the trust domain (the chain half of SPIFFE
    validation). ``ssl_cert_reqs=CERT_REQUIRED`` is the "m" in mTLS.

    Note: this is a point-in-time snapshot. SVIDs rotate; a long-running server
    should re-export and reload. Fine for a talk demo — don't ship as-is.
    """
    svid = source.get_x509_context().default_svid
    bundle = source.get_bundle_for_trust_domain(svid.spiffe_id.trust_domain)

    cert_path, key_path, ca_path = (directory / n for n in ("svid.pem", "svid.key", "bundle.pem"))
    svid.save(cert_path, key_path, Encoding.PEM)
    bundle.save(ca_path, Encoding.PEM)

    return {
        "ssl_certfile": str(cert_path),
        "ssl_keyfile": str(key_path),
        "ssl_ca_certs": str(ca_path),
        "ssl_cert_reqs": ssl.CERT_REQUIRED,
    }


def serve(*, authorized: list[str], host: str = "0.0.0.0", port: int = 8443) -> None:
    """Run the FastAPI mTLS listener, pulling identity from the Workload API."""
    source = X509Source(timeout_in_seconds=30)
    my_id = str(source.get_x509_context().default_svid.spiffe_id)
    print(f"[dispatch-fastapi] identity = {my_id}", flush=True)
    print(f"[dispatch-fastapi] only accepting: {', '.join(authorized)}", flush=True)
    app = create_app(authorized=authorized, server_id=my_id)
    try:
        with tempfile.TemporaryDirectory() as tmp:
            ssl_kwargs = write_ssl_material(source, Path(tmp))
            uvicorn.run(app, host=host, port=port, http=SpiffePeerProtocol, **ssl_kwargs)
    finally:
        source.close()


if __name__ == "__main__":
    from spiffe_demo.config import ORDER_ID

    # Dispatch: the only caller allowed to ship is the Order Service.
    serve(authorized=[str(ORDER_ID)])
