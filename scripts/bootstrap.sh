#!/usr/bin/env bash
# Bring up the whole demo. The join-token node-attestation flow needs a token
# generated at runtime, so we can't just `docker compose up` everything at once.
set -euo pipefail
cd "$(dirname "$0")/.."

export TRUST_DOMAIN="acme.internal"
export COMPOSE="docker compose"

echo "==> [1/5] starting SPIRE server"
$COMPOSE up -d spire-server
printf "    waiting for server to be healthy"
until $COMPOSE exec -T spire-server /opt/spire/bin/spire-server healthcheck >/dev/null 2>&1; do
  printf "."; sleep 1
done
echo " ok"

echo "==> [2/5] generating a join token for the agent"
TOKEN=$($COMPOSE exec -T spire-server /opt/spire/bin/spire-server token generate \
  | sed -n 's/^Token: //p' | tr -d '\r')
[ -n "$TOKEN" ] || { echo "ERROR: could not read a join token"; exit 1; }
export SPIRE_AGENT_JOIN_TOKEN="$TOKEN"
export AGENT_ID="spiffe://${TRUST_DOMAIN}/spire/agent/join_token/${TOKEN}"
echo "    agent id: $AGENT_ID"

# Persist the token where `docker compose` auto-reads it (.env). This keeps the
# agent's resolved config identical across every later compose command, so a
# stray `docker compose up <svc>` can't recreate the agent with a blank token
# and crash the stack. Updates only this key; other .env entries are preserved.
touch .env
{ grep -v '^SPIRE_AGENT_JOIN_TOKEN=' .env 2>/dev/null || true; \
  echo "SPIRE_AGENT_JOIN_TOKEN=$TOKEN"; } > .env.tmp && mv .env.tmp .env

echo "==> [3/5] starting SPIRE agent"
$COMPOSE up -d spire-agent
sleep 3

echo "==> [4/5] registering workload entries"
./spire/register-entries.sh

echo "==> [5/5] building and starting workloads (dispatch + order)"
$COMPOSE up -d --build dispatch order
# also build the attacker image now, so `just attack` runs current code with no
# build delay mid-demo (it's profile-gated, so this only builds — never starts it).
$COMPOSE --profile attack build omen >/dev/null 2>&1 || true

cat <<'EOF'

Up. Give the workloads a few seconds to fetch their first SVID, then:

  # Order's identity, fetched with no secret:
  curl -s localhost:8000/health | python -m json.tool

  # Charge + ship over SPIFFE mTLS (Order -> Dispatch):
  curl -s localhost:8000/checkout -H 'content-type: application/json' \
       -d '{"package_id":"pkg-1","address":"1 Main St","amount_cents":4999}' \
       | python -m json.tool

  # Watch Dispatch REJECT the attacker (valid cert, wrong identity):
  docker compose --profile attack run --rm omen

Tear down with:  docker compose down -v
EOF
