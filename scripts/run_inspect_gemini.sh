#!/usr/bin/env bash
# 带 SSL 信任修复地运行 Inspect 评测（解决 Netskope 下 ClientConnectorCertificateError）。
# 运行前会检查（并可自动拉起）REST API(:8000) + MCP(:3001)。
#
# 用法：
#   export GOOGLE_API_KEY='...'
#   ./scripts/run_inspect_gemini.sh
#   ./scripts/run_inspect_gemini.sh google/gemini-3.6-flash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate
# Inspect 按文件路径加载任务时需要项目根在 PYTHONPATH 中
export PYTHONPATH="${ROOT}${PYTHONPATH:+:$PYTHONPATH}"

MODEL="${1:-google/gemini-3.6-flash}"
TASK="${2:-evals/user_mcp_smoke.py}"
COMBINED="$ROOT/.certs/combined-ca.pem"
export USER_MCP_URL="${USER_MCP_URL:-http://127.0.0.1:3001/mcp}"
API_DOCS="${API_BASE_URL:-http://127.0.0.1:8000}/docs"

if [[ ! -f "$COMBINED" ]]; then
  bash "$ROOT/scripts/build_ssl_certs.sh"
fi

export SSL_CERT_FILE="$COMBINED"
export REQUESTS_CA_BUNDLE="$COMBINED"
export CURL_CA_BUNDLE="$COMBINED"

if [[ -z "${GOOGLE_API_KEY:-}${GEMINI_API_KEY:-}" ]]; then
  echo "请先设置 GOOGLE_API_KEY（或 GEMINI_API_KEY）" >&2
  exit 1
fi

port_listening() {
  local port="$1"
  lsof -nP -iTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1
}

# 预检：未起服务则自动 start_services.sh
need_start=0
port_listening 8000 || need_start=1
port_listening 3001 || need_start=1
if [[ "$need_start" -eq 1 ]]; then
  echo "API/MCP 未就绪，正在启动..."
  bash "$ROOT/scripts/start_services.sh"
fi

if ! port_listening 8000; then
  echo "ERROR: REST API 未监听 :8000。请先：uvicorn app.main:app --host 127.0.0.1 --port 8000" >&2
  exit 1
fi
if ! port_listening 3001; then
  echo "ERROR: MCP 未监听 :3001。请先：python -m mcp_server" >&2
  echo "（Inspect 报 ConnectError / streamablehttp_client 失败，通常就是 MCP 没起）" >&2
  exit 1
fi

# MCP 协议探活（比裸 curl 更准）
if ! python - <<'PY'
import asyncio
import os
import sys
from mcp.client import Client

url = os.environ.get("USER_MCP_URL", "http://127.0.0.1:3001/mcp")

async def main() -> None:
    async with Client(url) as client:
        tools = await client.list_tools()
        names = [t.name for t in tools.tools]
        if not names:
            raise RuntimeError("MCP list_tools 为空")
        print(f"MCP OK ({url}): {len(names)} tools")

try:
    asyncio.run(main())
except Exception as exc:
    print(f"ERROR: 无法连接 MCP: {exc}", file=sys.stderr)
    sys.exit(1)
PY
then
  echo "请确认已执行：python -m mcp_server" >&2
  exit 1
fi

echo "SSL_CERT_FILE=$SSL_CERT_FILE"
echo "API docs: $API_DOCS"
echo "model=$MODEL task=$TASK"
# 支持：
#   ./scripts/run_inspect_gemini.sh google/gemini-3.6-flash evals/bill_mcp_scenarios.py
#   ./scripts/run_inspect_gemini.sh google/gemini-3.6-flash evals/bill_mcp_scenarios.py@bill_share_flow
#   ./scripts/run_inspect_gemini.sh google/gemini-3.6-flash suite
if [[ "$TASK" == "suite" ]]; then
  exec inspect eval \
    evals/user_mcp_smoke.py \
    evals/user_profile_scenarios.py \
    evals/bill_mcp_scenarios.py \
    --model "$MODEL"
fi
exec inspect eval "$TASK" --model "$MODEL"
