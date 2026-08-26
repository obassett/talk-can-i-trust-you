from spiffe import SpiffeId

from spiffe_demo.config import DISPATCH_ID, ORDER_ID, TRUST_DOMAIN, workload_id


def test_ids_are_in_the_trust_domain():
    assert str(ORDER_ID.trust_domain) == "acme.internal"
    assert str(DISPATCH_ID.trust_domain) == "acme.internal"
    assert str(TRUST_DOMAIN) == "acme.internal"


def test_ids_are_distinct_and_correctly_formed():
    assert ORDER_ID != DISPATCH_ID
    assert str(ORDER_ID) == "spiffe://acme.internal/ns/prod/sa/order-service"
    assert str(DISPATCH_ID) == "spiffe://acme.internal/ns/prod/sa/dispatch-service"


def test_workload_id_helper_follows_k8s_convention():
    sid = workload_id("staging", "cart-service")
    assert isinstance(sid, SpiffeId)
    assert str(sid) == "spiffe://acme.internal/ns/staging/sa/cart-service"
