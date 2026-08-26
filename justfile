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

# follow all container logs
logs:
    docker compose logs -f

# tear everything down (including volumes)
down:
    docker compose down -v

# remove local build/test artifacts
clean:
    rm -rf .pytest_cache **/__pycache__ *.egg-info src/*.egg-info
