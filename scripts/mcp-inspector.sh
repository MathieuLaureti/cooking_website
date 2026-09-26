#!/usr/bin/env bash
# MCP Inspector wrapper for the cooking website (Streamable HTTP + MCP_API_KEY).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CONFIG="${ROOT}/tools/mcp-inspector/mcp.json"

if [[ -f "${ROOT}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  source "${ROOT}/.env"
  set +a
fi

BASE="${MCP_INSPECTOR_URL:-${PUBLIC_BASE_URL:-http://localhost:81}}"
BASE="${BASE%/}"
URL="${BASE}/mcp/"
KEY="${MCP_API_KEY:-}"
INSPECTOR=(npx --yes @modelcontextprotocol/inspector)

if [[ -z "${KEY}" ]]; then
  echo "error: set MCP_API_KEY in ${ROOT}/.env (used as Bearer token for inspector)" >&2
  exit 1
fi

auth_header=(--header "Authorization: Bearer ${KEY}")

run_inspector_ui() {
  echo "MCP Inspector UI → ${URL}"
  echo "Transport: Streamable HTTP (http). Auth: Bearer MCP_API_KEY"
  exec "${INSPECTOR[@]}" "${URL}" --transport http "${auth_header[@]}"
}

run_inspector_cli() {
  "${INSPECTOR[@]}" --cli "${URL}" --transport http "${auth_header[@]}" "$@"
}

run_inspector_cli_config() {
  local server=$1
  shift
  "${INSPECTOR[@]}" --cli --config "${CONFIG}" --server "${server}" "${auth_header[@]}" "$@"
}

http_head() {
  curl -sS -o /dev/null -w "HEAD ${URL} → HTTP %{http_code}\n" -I "${URL}" || true
}

http_get_json() {
  local path=$1
  local label=$2
  local code
  code="$(curl -sS -o /tmp/mcp-probe-body.json -w '%{http_code}' "${BASE}${path}")"
  echo "GET ${BASE}${path} (${label}) → HTTP ${code}"
  if [[ "${code}" == "200" ]]; then
    head -c 200 /tmp/mcp-probe-body.json
    echo ""
  fi
}

run_probe() {
  echo "=== MCP probe (public path + app) ==="
  echo "URL: ${URL}"
  echo ""

  if ! command -v curl >/dev/null 2>&1; then
    echo "warn: curl not found; skipping HTTP checks" >&2
  else
    http_head
    http_get_json "/.well-known/oauth-protected-resource" "OAuth protected resource"
    http_get_json "/.well-known/oauth-authorization-server" "OAuth AS metadata"
    echo ""
  fi

  echo "=== Inspector CLI (MCP JSON-RPC) ==="
  run_inspector_cli --method initialize
  echo ""
  run_inspector_cli --method tools/list
  echo ""
  run_inspector_cli --method tools/call --tool-name ping --tool-args-json '{}'
  echo ""
  echo "probe finished"
}

usage() {
  cat <<EOF
Usage: $(basename "$0") [ui|probe|cli|config-cli] [inspector args...]

  ui          Open MCP Inspector web UI (default)
  probe       curl discovery + initialize, tools/list, tools/call ping
  cli         Pass-through: $(basename "$0") cli --method tools/list
  config-cli  Use tools/mcp-inspector/mcp.json: $(basename "$0") config-cli cooking-homelab --method tools/list

Environment (from .env):
  PUBLIC_BASE_URL   Base site URL (prod: https://www.homelabdu204.ca/recipes)
  MCP_API_KEY       Bearer token for /mcp/

  MCP_INSPECTOR_URL  Override base URL (trailing slash optional)
EOF
}

MODE="${1:-ui}"
shift || true

case "${MODE}" in
  ui)
    run_inspector_ui
    ;;
  probe)
    run_probe
    ;;
  cli)
    run_inspector_cli "$@"
    ;;
  config-cli)
    SERVER="${1:-cooking-homelab}"
    shift || true
    run_inspector_cli_config "${SERVER}" "$@"
    ;;
  -h | --help | help)
    usage
    ;;
  *)
    echo "unknown mode: ${MODE}" >&2
    usage >&2
    exit 1
    ;;
esac
