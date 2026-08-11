#!/usr/bin/env bash
# 生成本机可用的 CA 包：certifi + Netskope（若存在），解决 ClientConnectorCertificateError。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/.certs"
OUT="$OUT_DIR/combined-ca.pem"

source "$ROOT/.venv/bin/activate"
CERTIFI_PEM="$(python -c 'import certifi; print(certifi.where())')"

mkdir -p "$OUT_DIR"
{
  echo "# certifi"
  cat "$CERTIFI_PEM"
  for f in \
    "/Library/Application Support/Netskope/STAgent/download/nscacert.pem" \
    "/Library/Application Support/Netskope/STAgent/download/nstenantcert.pem"
  do
    if [[ -f "$f" ]]; then
      echo ""
      echo "# $(basename "$f")"
      cat "$f"
    fi
  done
} > "$OUT"

echo "Wrote $OUT"
