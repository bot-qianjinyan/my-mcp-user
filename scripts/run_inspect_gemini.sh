#!/usr/bin/env bash
# 带 SSL 信任修复地运行 Inspect 评测（解决 Netskope 下 ClientConnectorCertificateError）。
#
# 用法：
#   export GOOGLE_API_KEY='...'
#   ./scripts/run_inspect_gemini.sh
#   ./scripts/run_inspect_gemini.sh google/gemini-3.6-flash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
source .venv/bin/activate

MODEL="${1:-google/gemini-3.6-flash}"
TASK="${2:-evals/user_mcp_smoke.py}"
COMBINED="$ROOT/.certs/combined-ca.pem"

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

echo "SSL_CERT_FILE=$SSL_CERT_FILE"
echo "model=$MODEL task=$TASK"
exec inspect eval "$TASK" --model "$MODEL"
