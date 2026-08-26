"""Shared code for the 'Can I Trust You?' SPIFFE talk demo.

The service-to-service identity lives in `config` (SPIFFE IDs / trust domain),
the wire format in `protocol`, the (pure) business logic in `orders`, and the
TLS-socket I/O helpers in `sslio`.
"""
