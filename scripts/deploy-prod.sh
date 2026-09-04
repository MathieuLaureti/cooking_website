#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/home/mlaureti/cooking_website"
COMPOSE_FILE="docker-compose.prod.yml"
BRANCH="master"
HEALTH_URL="http://localhost/api/health"
HEALTH_RETRIES=30
HEALTH_INTERVAL=5

log() {
  echo "[$(date -Iseconds)] $*"
}

log "Deploying prod from ${REPO_DIR}"

cd "${REPO_DIR}"

if [[ ! -f .env ]]; then
  log "ERROR: .env not found at ${REPO_DIR}/.env"
  exit 1
fi

log "Fetching origin/${BRANCH}"
git fetch origin "${BRANCH}"
git reset --hard "origin/${BRANCH}"

log "Building prod images"
docker compose -f "${COMPOSE_FILE}" build

log "Starting prod stack"
docker compose -f "${COMPOSE_FILE}" up -d --remove-orphans

log "Waiting for ${HEALTH_URL}"
for i in $(seq 1 "${HEALTH_RETRIES}"); do
  if curl -sf "${HEALTH_URL}" >/dev/null; then
    log "Health check passed"
    exit 0
  fi
  log "Health check attempt ${i}/${HEALTH_RETRIES} failed; retrying in ${HEALTH_INTERVAL}s"
  sleep "${HEALTH_INTERVAL}"
done

log "ERROR: Health check failed after ${HEALTH_RETRIES} attempts"
exit 1
