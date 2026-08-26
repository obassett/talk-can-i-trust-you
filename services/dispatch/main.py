"""Dispatch Service — the mTLS server.

This is the payoff of the talk in ~20 lines: Dispatch accepts a connection
ONLY if the peer proves, cryptographically, that it is the Order Service.
A valid certificate from the trust domain is not enough — it must be the
*right* SPIFFE ID. That single line (`authorize_fn=authorize_id(ORDER_ID)`)
is what closes Round 3's gap.

Run: python -m services.dispatch.main   (needs a reachable Workload API socket)
"""

from __future__ import annotations

from OpenSSL import SSL
from spiffe import X509Source
from spiffetls import ListenOptions, listen
from spiffetls.mode import ServerTlsMode
from spiffetls.tlsconfig.authorize import authorize_id

from spiffe_demo.config import DISPATCH_LISTEN, ORDER_ID
from spiffe_demo.protocol import ShipResponse, decode_request, encode_response
from spiffe_demo.sslio import recv_line, send_all


def handle(conn: SSL.Connection) -> None:
    try:
        line = recv_line(conn)
        if not line:
            return
        req = decode_request(line)

        # Business rule from the talk: never ship an unpaid order.
        if not req.charged:
            resp = ShipResponse(
                status="REJECTED_UNPAID",
                package_id=req.package_id,
                detail="no matching payment",
            )
        else:
            # warehouse.dispatch(req.package_id, req.address)
            resp = ShipResponse(
                status="SHIPPED",
                package_id=req.package_id,
                detail=f"to {req.address}",
            )

        send_all(conn, encode_response(resp))
        print(f"[dispatch] {resp.status} package={req.package_id}", flush=True)
    except SSL.Error as e:
        # A peer that isn't the Order Service fails the mTLS handshake right here.
        # That's the authorization model doing its job — log it and drop the
        # connection. A rejected client must NEVER take the server down.
        print(f"[dispatch] REJECTED a peer that isn't {ORDER_ID}: {e}", flush=True)
    except Exception as e:  # never let one bad connection kill Dispatch
        print(f"[dispatch] dropped a bad connection: {type(e).__name__}: {e}", flush=True)
    finally:
        try:
            conn.close()
        except Exception:
            pass


def main() -> None:
    source = X509Source(timeout_in_seconds=30)
    print(f"[dispatch] identity = {source.svid.spiffe_id}", flush=True)

    options = ListenOptions(
        tls_mode=ServerTlsMode.MTLS,
        # The whole authorization model: only the Order Service may connect.
        authorize_fn=authorize_id(ORDER_ID),
    )
    sock = listen(DISPATCH_LISTEN, source, options)
    print(f"[dispatch] listening on {DISPATCH_LISTEN}", flush=True)
    print(f"[dispatch] the ONLY caller I will accept is {ORDER_ID}", flush=True)

    try:
        while True:
            try:
                conn, _addr = sock.accept()
            except SSL.Error as e:
                # Some handshake failures surface at accept() rather than at recv().
                print(f"[dispatch] REJECTED a peer at handshake: {e}", flush=True)
                continue
            handle(conn)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            sock.close()
        finally:
            source.close()


if __name__ == "__main__":
    main()
