from spiffe_demo.protocol import (
    ShipRequest,
    ShipResponse,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
)


def test_request_roundtrip():
    req = ShipRequest(package_id="pkg-1", address="1 Main St", charged=True)
    wire = encode_request(req)
    assert wire.endswith(b"\n")  # newline-framed
    assert decode_request(wire) == req


def test_response_roundtrip():
    resp = ShipResponse(status="SHIPPED", package_id="pkg-1", detail="to 1 Main St")
    wire = encode_response(resp)
    assert wire.endswith(b"\n")
    assert decode_response(wire) == resp


def test_charged_defaults_to_false():
    # Omen's unpaid request: charged must not silently default to True.
    req = ShipRequest(package_id="xbox", address="lair")
    assert req.charged is False
