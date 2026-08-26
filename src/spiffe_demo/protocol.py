"""The tiny newline-delimited JSON protocol Order and Dispatch speak.

Deliberately minimal: one JSON object per line, in each direction. The point of
the demo is the *identity* on the connection, not the payload format.
"""

from __future__ import annotations

from pydantic import BaseModel


class ShipRequest(BaseModel):
    package_id: str
    address: str
    # Was the customer actually charged? In Round 1 of the talk, Omen ships
    # without charging — so Dispatch treats this as a first-class field.
    charged: bool = False


class ShipResponse(BaseModel):
    status: str  # "SHIPPED" | "REJECTED_UNPAID" | ...
    package_id: str
    detail: str = ""


def encode_request(req: ShipRequest) -> bytes:
    return (req.model_dump_json() + "\n").encode()


def decode_request(raw: bytes) -> ShipRequest:
    return ShipRequest.model_validate_json(raw.decode().strip())


def encode_response(resp: ShipResponse) -> bytes:
    return (resp.model_dump_json() + "\n").encode()


def decode_response(raw: bytes) -> ShipResponse:
    return ShipResponse.model_validate_json(raw.decode().strip())
