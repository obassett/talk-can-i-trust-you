# Can I Trust You? — SPIFFE demo repo

Companion code for the talk *"Can I Trust You? Service-to-Service Identity with
SPIFFE."* Two services — **Order** and **Dispatch** — authenticate to each
other with SPIFFE X.509-SVIDs over mutual TLS. Dispatch will only ship a package
if the caller can *prove* it is the Order Service. Not "inside the network."
Not "has a shared key." The right cryptographic identity, or nothing.


> Verified against **`spiffe` 0.3.0** and **`spiffe-tls` 0.4.0**. The Python is
> the focus and is tested. The SPIRE/docker wiring is a demo-grade convenience
> (see [Caveats](#caveats)).

## What's here

| Path | What it is |
|------|------------|
| `src/spiffe_demo/config.py` | The two SPIFFE IDs + trust domain — the entire authz model |
| `src/spiffe_demo/protocol.py` | Tiny newline-JSON wire format (`ShipRequest`/`ShipResponse`) |
| `src/spiffe_demo/orders.py` | Pure "charge then ship" logic (unit-tested) |
| `src/spiffe_demo/sslio.py` | pyOpenSSL send/recv helpers (WantRead/WantWrite safe) |
| `services/dispatch/main.py` | mTLS **server** — `authorize_id(ORDER_ID)` |
| `services/order/main.py` | FastAPI **client** — charges, then `dial()`s Dispatch |
| `scripts/whoami.py` | Fetch & print this workload's SPIFFE ID (no secret) |
| `scripts/jwt_svid.py` | Fetch an audience-scoped JWT-SVID |
| `scripts/omen.py` | The attacker — gets rejected by Dispatch |
| `scripts/httpx_client.py` | Reference: SPIFFE mTLS with `httpx` |
| `spire/` | SPIRE server/agent config + registration entries |
| `docker-compose.yml`, `scripts/bootstrap.sh` | One-command demo environment |

## Presenting the slides

The deck is [`docs/slides.md`](docs/slides.md), a terminal presentation for
[presenterm](https://github.com/mfontanini/presenterm). Run it with:

```bash
just slides          # light theme (the default) — use this on a projector
just slides dark     # dark theme — use this for screen-share
just slides <theme>  # any other presenterm theme name
```

Use **light** on a projector and **dark** for screen-share. The diagrams are drawn to
work on both backgrounds (see [`docs/diagrams/README.md`](docs/diagrams/README.md)).

## How it maps to the talk

Each demo slide carries a 🔑 key — a `just` command you run live to show exactly
what the slide's code does. Bring the stack up first with `just up`, then:

| Slide | Shows | Source | 🔑 Live command |
| --- | --- | --- | --- |
| 27 | get an identity, no secret | `scripts/whoami.py` | `just whoami` |
| 28 | server authorizes a specific ID | `services/dispatch/main.py` | `just attack` — Omen rejected |
| 29 | client dials, pins server ID | `services/order/main.py` | `just checkout` — package ships |
| 30 | SPIFFE + httpx | `scripts/httpx_demo.py` (`httpx_client.py` = ref) | `just httpx` |
| 31 | JWT-SVID beyond the cluster | `scripts/jwt_svid.py` | `just jwt` |
| "Omen doesn't stand a chance" | valid cert, wrong identity | `scripts/omen.py` | `just attack` |

`just` echoes each command before running it, so the audience sees the exact
invocation and its output. `whoami`/`jwt` run inside the `order` container (that's
where the Workload API socket and the registered `order-service` identity live);
`checkout` hits the published port; `attack` runs the `omen` profile.

## Quickstart — just the Python (no Docker)

The unit tests need nothing but the packages:

```bash
python -m venv .venv && source .venv/bin/activate
just install         # pip install -e ".[dev]"
just test            # 10 passing tests, no SPIRE required
```

If you already have a SPIRE agent (or any Workload API implementation) reachable,
point `SPIFFE_ENDPOINT_SOCKET` at it and:

```bash
export SPIFFE_ENDPOINT_SOCKET=unix:///run/spire/sockets/api.sock
python scripts/whoami.py   # prints your SPIFFE ID + the SVID's expiry
```

(The `just whoami` recipe targets the Docker demo below — it execs inside the
`order` container. For a host-side run, call the script directly as above.)

## Full demo — SPIRE + both services in Docker

Requires Docker with the Compose plugin.

```bash
just up              # ./scripts/bootstrap.sh
```

`bootstrap.sh` starts the SPIRE server, generates a join token, starts the
agent, registers the workload entries (binding each SPIFFE ID to a Docker
label), then builds and starts Order and Dispatch. Then:

```bash
# Order's identity, fetched with no secret:
curl -s localhost:8000/health | python -m json.tool

# Charge + ship over SPIFFE mTLS (Order -> Dispatch):
just checkout
```

You should see `"status": "SHIPPED"`.

### The payoff: watch Omen get rejected

Omen has a **valid** SVID — just not the Order Service's. Dispatch refuses it:

```bash
just attack          # docker compose --profile attack run --rm omen
```

Expected output is a rejection: a valid certificate from the trust domain is
**not** enough; the handshake only completes for `order-service`. That's the gap
Round 3 (long-lived mTLS with "any cert from our CA is fine") left open, closed.

Tear down:

```bash
just down            # docker compose down -v
```

## The one line that matters

Everything above is scaffolding around this, in `services/dispatch/main.py`:

```python
options = ListenOptions(
    tls_mode=ServerTlsMode.MTLS,
    authorize_fn=authorize_id(ORDER_ID),   # only the Order Service, full stop
)
```

Swap `authorize_id` for `authorize_one_of({...})` or `authorize_member_of(td)`
to widen the policy deliberately, instead of "any valid cert" by accident.

## Caveats

- **SPIRE wiring is demo-grade.** The agent runs `privileged` with `pid: host`
  and `insecure_bootstrap` so the `docker` workload attestor can resolve caller
  containers on a laptop. Do not copy this into production; there you'd use
  proper node attestation (k8s PSAT, AWS IID, a custom attestor, …) and ship the
  trust bundle out-of-band.
- **Image tags / plugin fields drift between SPIRE versions.** This targets
  `ghcr.io/spiffe/spire-*:1.9.6`. On another version you may need to adjust the
  image tag or a plugin field name. The Python code does not depend on any of
  this — only on a reachable Workload API socket.
- **`spiffe-tls` is experimental.** Great for these patterns; pin versions and
  test SVID rotation under load before leaning on it in production.
- Dispatch speaks a raw mTLS socket protocol (matching the talk's `listen()`/
  `dial()` slides), so `scripts/httpx_client.py` is a reference for the
  *HTTP* pattern rather than wired to Dispatch.

## License

Demo code, provided as-is for the talk. Use freely.
