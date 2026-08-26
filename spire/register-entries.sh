#!/usr/bin/env bash
# Create SPIRE registration entries that bind each SPIFFE ID to a workload's
# Docker label. Requires:
#   AGENT_ID  - the attested agent's SPIFFE ID (set by bootstrap.sh)
#   a running spire-server container
set -euo pipefail

: "${AGENT_ID:?set AGENT_ID to the agent SPIFFE ID - bootstrap.sh does this}"
TD="${TRUST_DOMAIN:-acme.internal}"
COMPOSE="${COMPOSE:-docker compose}"

create() {  # $1 = service account (SPIFFE path)   $2 = compose service label
  echo "    - spiffe://${TD}/ns/prod/sa/$1  <=  docker service '$2'"
  $COMPOSE exec -T spire-server /opt/spire/bin/spire-server entry create \
    -parentID "$AGENT_ID" \
    -spiffeID "spiffe://${TD}/ns/prod/sa/$1" \
    -selector "docker:label:com.docker.compose.service:$2" >/dev/null || true
}

create order-service    order
create dispatch-service dispatch

# Omen gets a VALID identity that is deliberately NOT order-service. This is
# what makes the rejection demo meaningful: a valid cert isn't enough to call
# Dispatch — it has to be the *right* SPIFFE ID.
create omen             omen
