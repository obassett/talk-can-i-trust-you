# List available recipes (default when you just run `just`)
default:
    @just --list

# install package + dev deps into the current env
install:
    pip install -e ".[dev]"

# run the unit tests (no SPIRE needed)
test:
    pytest

# DEMO slide 27 — Order fetches its SPIFFE ID from the Workload API, no secret
whoami:
    docker compose exec -T order python scripts/whoami.py

# DEMO slide 30 — httpx + SpiffeSSLContext calls a SPIFFE-mTLS HTTPS service
httpx:
    docker compose exec -T order python scripts/httpx_demo.py

# DEMO slide 31 — fetch an audience-scoped JWT-SVID (order-service)
jwt:
    docker compose exec -T order python scripts/jwt_svid.py

# bring up SPIRE + services (generates a join token)
up:
    ./scripts/bootstrap.sh

# DEMO slide 29 — Order dials Dispatch over SPIFFE mTLS and ships the package
checkout:
    curl -s localhost:8000/checkout -H 'content-type: application/json' \
      -d '{"package_id":"pkg-1","address":"1 Main St","amount_cents":4999}' \
      | python -m json.tool

# DEMO slide 28 — Omen (valid cert, WRONG identity) gets rejected by Dispatch
attack:
    docker compose --profile attack run --rm omen

# Starts the listener in the dispatch container (dispatch-service), then
# order-service calls it; the JSON response shows BOTH SPIFFE IDs. Needs the new
# code baked into the images — `just up` (re)builds dispatch + order, so run that
# first if you haven't since adding this.
# DEMO — FastAPI listener doing real SPIFFE mTLS (order-service → dispatch-service)
fastapi-demo:
    #!/usr/bin/env bash
    set -euo pipefail
    ORDER_ID="spiffe://acme.internal/ns/prod/sa/order-service"
    KILL='import glob,os; [os.kill(int(p.split("/")[2]),9) for p in glob.glob("/proc/[0-9]*/cmdline") if b"fastapi_mtls_spire" in open(p,"rb").read()]'
    docker compose exec -T dispatch python -c "$KILL" 2>/dev/null || true
    echo "→ starting FastAPI SPIFFE-mTLS listener in dispatch (:9443, authorizing order-service)"
    docker compose exec -d dispatch python scripts/fastapi_mtls_spire.py serve --port 9443 --authorize "$ORDER_ID"
    for _ in $(seq 1 40); do
      docker compose exec -T dispatch python -c 'import socket; socket.create_connection(("127.0.0.1",9443),1).close()' 2>/dev/null && break
      sleep 0.5
    done
    echo "→ order-service calls the dispatch-service listener over mutual SPIFFE mTLS:"
    docker compose exec -T order python scripts/fastapi_mtls_spire.py call --url https://dispatch:9443/ship
    docker compose exec -T dispatch python -c "$KILL" 2>/dev/null || true

# ---- `<demo>-code`: print the code a demo runs, for showing on stage ----

# print a source file, syntax-highlighted if `bat` is installed
_code FILE:
    @bat --style=plain --paging=never {{FILE}} 2>/dev/null || cat {{FILE}}

# show the source behind each demo
whoami-code:
    @just _code scripts/whoami.py

httpx-code:
    @just _code scripts/httpx_demo.py

jwt-code:
    @just _code scripts/jwt_svid.py

checkout-code:
    @just _code services/order/main.py

attack-code:
    @just _code scripts/omen.py

fastapi-demo-code:
    @just _code src/spiffe_demo/fastapi_mtls.py

# follow all container logs
logs:
    docker compose logs -f

# tear everything down (including volumes)
down:
    docker compose down -v

# remove local build/test artifacts
clean:
    rm -rf .pytest_cache **/__pycache__ *.egg-info src/*.egg-info
