#!/usr/bin/env bash
# One-time setup for the self-hosted GitHub Actions runner (Linux ARM64).
# Requires: gh CLI authenticated with repo scope, docker usable without sudo.
set -euo pipefail

REPO="MathieuLaureti/cooking_website"
RUNNER_DIR="${HOME}/actions-runner"
RUNNER_LABEL="prod"

log() {
  echo "[$(date -Iseconds)] $*"
}

if ! command -v gh >/dev/null; then
  log "ERROR: gh CLI is required"
  exit 1
fi

if [[ "$(uname -m)" != "aarch64" ]]; then
  log "ERROR: This script targets Linux ARM64 (aarch64)"
  exit 1
fi

RUNNER_VERSION=$(curl -fsSL https://api.github.com/repos/actions/runner/releases/latest | grep -oP '"tag_name": "\Kv[^"]+')
log "Latest runner release: ${RUNNER_VERSION}"

mkdir -p "${RUNNER_DIR}"
cd "${RUNNER_DIR}"

if [[ ! -f ./config.sh ]]; then
  log "Downloading runner to ${RUNNER_DIR}"
  curl -fsSL -o actions-runner.tar.gz \
    "https://github.com/actions/runner/releases/download/${RUNNER_VERSION}/actions-runner-linux-arm64-${RUNNER_VERSION#v}.tar.gz"
  tar xzf actions-runner.tar.gz
  rm actions-runner.tar.gz
fi

if [[ -f ./.runner ]]; then
  log "Runner already configured in ${RUNNER_DIR}"
else
  log "Requesting registration token for ${REPO}"
  TOKEN=$(gh api -X POST "repos/${REPO}/actions/runners/registration-token" --jq .token)
  ./config.sh \
    --url "https://github.com/${REPO}" \
    --token "${TOKEN}" \
    --labels "${RUNNER_LABEL}" \
    --unattended \
    --replace
fi

if systemctl is-active --quiet actions.runner.* 2>/dev/null; then
  log "Runner service already running"
else
  log "Installing and starting runner systemd service"
  sudo ./svc.sh install
  sudo ./svc.sh start
fi

log "Runner setup complete. Verify in GitHub → Settings → Actions → Runners."
