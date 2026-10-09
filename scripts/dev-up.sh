#!/usr/bin/env bash
# Start the TAP local development stack (Postgres, Redis, NATS, Qdrant,
# Temporal, OPA), wait for health, apply the DB schema, and seed a demo tenant.
#
# Usage: ./scripts/dev-up.sh [--no-seed]
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/platform/docker-compose.dev.yaml"
SCHEMA_FILE="$REPO_ROOT/platform/db/schema.sql"
PROJECT="tap-dev"
SEED=true
TIMEOUT="${TAP_DEV_TIMEOUT:-180}"

[[ "${1:-}" == "--no-seed" ]] && SEED=false

log() { printf '\033[1;34m[dev-up]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[dev-up]\033[0m %s\n' "$*" >&2; exit 1; }

command -v docker >/dev/null || die "docker is required"
docker compose version >/dev/null 2>&1 || die "docker compose v2 is required"
[[ -f "$COMPOSE_FILE" ]] || die "compose file not found: $COMPOSE_FILE"

log "Starting compose stack ($COMPOSE_FILE)"
docker compose -f "$COMPOSE_FILE" -p "$PROJECT" up -d --remove-orphans

log "Waiting for services to report healthy (timeout ${TIMEOUT}s)"
deadline=$((SECONDS + TIMEOUT))
while :; do
    unhealthy=""
    for cid in $(docker compose -f "$COMPOSE_FILE" -p "$PROJECT" ps -q); do
        status=$(docker inspect -f \
            '{{.Name}} {{.State.Status}} {{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' \
            "$cid")
        name=$(echo "$status" | awk '{print $1}')
        state=$(echo "$status" | awk '{print $2}')
        health=$(echo "$status" | awk '{print $3}')
        if [[ "$state" != "running" || ( "$health" != "none" && "$health" != "healthy" ) ]]; then
            unhealthy+="${name}: ${state}/${health}"$'\n'
        fi
    done
    if [[ -z "$unhealthy" ]]; then
        log "All services healthy"
        break
    fi
    if (( SECONDS >= deadline )); then
        printf '%s' "$unhealthy" >&2
        die "services not healthy after ${TIMEOUT}s"
    fi
    sleep 3
done

if [[ -f "$SCHEMA_FILE" ]]; then
    log "Applying database schema"
    docker compose -f "$COMPOSE_FILE" -p "$PROJECT" exec -T postgres \
        psql -v ON_ERROR_STOP=1 -U "${TAP_DB_USER:-tap}" -d "${TAP_DB_NAME:-tap}" < "$SCHEMA_FILE"
else
    log "No schema file at platform/db/schema.sql — skipping"
fi

if $SEED; then
    log "Seeding demo tenant"
    if command -v python3 >/dev/null && python3 -c 'import httpx' 2>/dev/null; then
        python3 "$REPO_ROOT/scripts/seed-demo.py" \
            || log "seed failed (is tap-server running?); rerun: python scripts/seed-demo.py"
    else
        log "httpx not installed — skipping seed; run: pip install httpx && python scripts/seed-demo.py"
    fi
fi

log "Dev stack is up:"
log "  Postgres   localhost:5432   Redis    localhost:6379"
log "  NATS       localhost:4222   Qdrant   localhost:6333"
log "  Temporal   localhost:7233 (UI :8233)   OPA   localhost:8181"
log "Next: pip install -e ./platform -e ./sdk && tap-server --config platform/config/dev.yaml"
