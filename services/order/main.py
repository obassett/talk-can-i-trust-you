"""Order Service — a FastAPI app that is the client half of the mTLS pair.

POST /checkout charges the customer, then calls Dispatch over SPIFFE mTLS to
ship. Two things worth noticing:
  * We never present a secret to obtain our identity — X509Source pulls our
    SVID from the local Workload API socket and rotates it in the background.
  * We pin Dispatch's identity too (`authorize_id(DISPATCH_ID)`), so Order
    won't talk to an impostor Dispatch either. Authentication is mutual.

Run: uvicorn services.order.main:app --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from spiffe import X509Source
from spiffetls import dial
from spiffetls.tlsconfig.authorize import authorize_id

from spiffe_demo.config import DISPATCH_ADDR, DISPATCH_ID
from spiffe_demo.orders import PaymentError, build_ship_request
from spiffe_demo.protocol import decode_response, encode_request
from spiffe_demo.sslio import recv_line, send_all

# One long-lived X509Source for the process; it keeps our SVID fresh as it
# rotates, so every request uses a currently-valid identity.
_source: X509Source | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _source
    _source = X509Source(timeout_in_seconds=30)
    print(f"[order] identity = {_source.svid.spiffe_id}", flush=True)
    yield
    if _source is not None:
        _source.close()


app = FastAPI(title="Order Service", lifespan=lifespan)


class Checkout(BaseModel):
    package_id: str
    address: str
    amount_cents: int = 4999


@app.get("/health")
def health() -> dict:
    sid = str(_source.svid.spiffe_id) if _source else None
    return {"status": "ok", "identity": sid}


@app.post("/checkout")
def checkout(order: Checkout) -> dict:
    assert _source is not None, "X509Source not initialised"

    # 1) Charge first. If this fails we never build a ship request.
    try:
        req = build_ship_request(order.package_id, order.address, order.amount_cents)
    except PaymentError as e:
        raise HTTPException(status_code=402, detail=str(e))

    # 2) Ship over SPIFFE mTLS, verifying we're really talking to Dispatch.
    conn = dial(DISPATCH_ADDR, _source, authorize_fn=authorize_id(DISPATCH_ID))
    conn.setblocking(True)
    try:
        send_all(conn, encode_request(req))
        resp = decode_response(recv_line(conn))
    finally:
        conn.close()

    if resp.status != "SHIPPED":
        raise HTTPException(status_code=502, detail=resp.model_dump())

    return {"charged": True, "dispatch": resp.model_dump()}
