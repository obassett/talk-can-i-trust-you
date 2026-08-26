"""Slide 30 (live) — dropping SPIFFE into httpx, end to end.

`scripts/httpx_client.py` is the reference *snippet* (Dispatch here speaks a raw
mTLS socket, not HTTPS, so there's nothing HTTP to point it at). This runnable
demo stands up a tiny SPIFFE-mTLS HTTPS `/health` service from our live SVID,
then calls it with the exact pattern from the slide:

    ssl_context = SpiffeSSLContext(source)      # stdlib-compatible
    client = httpx.Client(verify=ssl_context)
    client.get("https://.../health")

Both ends authenticate with the workload's real, rotating SVID from the Workload
API — no secret on disk, no shared key. Run inside a workload:  just httpx
"""

from __future__ import annotations

import http.server
import logging
import os
import ssl
import tempfile
import threading

import httpx
from cryptography.hazmat.primitives import serialization as _ser
from spiffe import X509Source
from spiffetls import SpiffeSSLContext

# keep the live demo output clean
logging.getLogger("spiffe").setLevel(logging.CRITICAL)


def _write_identity_files(source: X509Source, tmp: str) -> tuple[str, str, str]:
    """Materialise the current SVID (cert+key) and trust bundle as PEM files.

    Only the *server* side needs files, because Python's stdlib HTTPS server
    loads its context from paths. The client side (the slide's point) never
    touches disk — it uses SpiffeSSLContext straight from the Workload API.
    """
    svid = source.get_x509_context().default_svid
    td = svid.spiffe_id.trust_domain
    authorities = source.get_bundle_for_trust_domain(td).x509_authorities

    cert_p = os.path.join(tmp, "svid.pem")
    key_p = os.path.join(tmp, "svid.key")
    ca_p = os.path.join(tmp, "bundle.pem")
    with open(cert_p, "wb") as f:
        for cert in svid.cert_chain:
            f.write(cert.public_bytes(_ser.Encoding.PEM))
    with open(key_p, "wb") as f:
        f.write(svid.private_key.private_bytes(
            _ser.Encoding.PEM, _ser.PrivateFormat.PKCS8, _ser.NoEncryption()))
    with open(ca_p, "wb") as f:
        for authority in authorities:
            f.write(authority.public_bytes(_ser.Encoding.PEM))
    return cert_p, key_p, ca_p


def _serve_mtls_health(source: X509Source, tmp: str) -> tuple[http.server.HTTPServer, str]:
    """Start a SPIFFE-mTLS HTTPS server exposing /health on an ephemeral port."""
    svid_id = source.get_x509_context().default_svid.spiffe_id
    cert_p, key_p, ca_p = _write_identity_files(source, tmp)

    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_p, key_p)
    ctx.load_verify_locations(ca_p)
    ctx.verify_mode = ssl.CERT_REQUIRED  # mutual: the caller must present an SVID too

    class Health(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            body = f'{{"status":"ok","served_by":"{svid_id}"}}'.encode()
            self.send_response(200)
            self.send_header("content-type", "application/json")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):  # silence per-request logging
            pass

    httpd = http.server.HTTPServer(("127.0.0.1", 0), Health)
    httpd.socket = ctx.wrap_socket(httpd.socket, server_side=True)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    port = httpd.socket.getsockname()[1]
    print(f"[server] SPIFFE-mTLS HTTPS /health up as {svid_id}", flush=True)
    return httpd, f"https://127.0.0.1:{port}/health"


def main() -> None:
    with X509Source(timeout_in_seconds=30) as source, tempfile.TemporaryDirectory() as tmp:
        httpd, url = _serve_mtls_health(source, tmp)
        try:
            # ---- this block is exactly slide 30 ----
            ssl_context = SpiffeSSLContext(source)      # refreshes as the SVID rotates
            client = httpx.Client(verify=ssl_context)
            print(f"[client] httpx GET {url}  (verify=SpiffeSSLContext)", flush=True)
            resp = client.get(url)
            # ----------------------------------------
            print(f"[client] {resp.status_code} {resp.text}", flush=True)
            print("[client] mTLS with both sides' SVIDs — no shared secret, no cert on the client's disk", flush=True)
        finally:
            httpd.shutdown()


if __name__ == "__main__":
    main()
