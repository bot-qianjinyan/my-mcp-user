#!/usr/bin/env bash
# 启动本仓库评测所需的 REST API(:8000) + MCP(:3001)。
# 若端口已占用则跳过。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate

API_HOST="${API_HOST:-127.0.0.1}"
API_PORT="${API_PORT:-8000}"
MCP_HOST="${MCP_HOST:-127.0.0.1}"
MCP_PORT="${MCP_PORT:-3001}"
LOG_DIR="${TMPDIR:-/tmp}/my-mcp-services"
mkdir -p "$LOG_DIR"

port_listening() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

start_api() {
  if port_listening "$API_PORT"; then
    echo "API already listening on ${API_HOST}:${API_PORT}"
    return 0
  fi
  echo "Starting API on ${API_HOST}:${API_PORT} ..."
  nohup uvicorn app.main:app --host "$API_HOST" --port "$API_PORT" \
    >"$LOG_DIR/api.log" 2>&1 &
  echo $! >"$LOG_DIR/api.pid"
}

start_mcp() {
  if port_listening "$MCP_PORT"; then
    echo "MCP already listening on ${MCP_HOST}:${MCP_PORT}"
    return 0
  fi
  echo "Starting MCP on ${MCP_HOST}:${MCP_PORT} ..."
  nohup python -m mcp_server \
    >"$LOG_DIR/mcp.log" 2>&1 &
  echo $! >"$LOG_DIR/mcp.pid"
}

wait_http() {
  local url="$1"
  local name="$2"
  local i
  for i in $(seq 1 30); do
    if curl -s -o /dev/null --connect-timeout 1 "$url"; then
      echo "$name ready: $url"
      return 0
    fi
    # MCP /mcp 常对裸 GET 返回 4xx，但仍说明端口通了
    if curl -s -o /dev/null --connect-timeout 1 -w '' "$url" || \
       nc -z "${url#http://}" 2>/dev/null; then
      :
    fi
    sleep 0.3
  done
  echo "$name not ready: $url" >&2
  return 1
}

wait_port() {
  local host="$1"
  local port="$2"
  local name="$3"
  local i
  for i in $(seq 1 40); do
    if port_listening "$port"; then
      echo "$name listening on ${host}:${port}"
      return 0
    fi
    sleep 0.25
  done
  echo "$name failed to listen on ${host}:${port}" >&2
  echo "See logs under $LOG_DIR" >&2
  return 1
}

start_api
start_mcp
wait_port "$API_HOST" "$API_PORT" "API"
wait_port "$MCP_HOST" "$MCP_PORT" "MCP"

# 轻量协议探活
if ! curl -s -o /dev/null -w '' "http://${API_HOST}:${API_PORT}/docs"; then
  echo "WARN: API /docs not reachable" >&2
fi
echo "Services up. Logs: $LOG_DIR"
