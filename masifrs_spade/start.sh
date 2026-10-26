#!/usr/bin/env bash
# MAS-IFRS (SPADE 4.1.4) — sobe os agentes e o monitor.
#
# Uso:
#   ./start.sh                       # agentes + monitor (servidor XMPP já em execução)
#   ./start.sh --embedded-server     # idem, com servidor XMPP embutido do SPADE
#   ./start.sh --only meter predictor
# Variáveis: MONITOR_HOST (localhost) | MONITOR_PORT (8765)
#            MONITOR_CERT / MONITOR_KEY (certificado próprio; senão gera um autoassinado)
# O monitor é servido em HTTPS: https://localhost:8765
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
VENV="$HERE/../.venv-spade"
PY="$VENV/bin/python"
MONITOR_HOST="${MONITOR_HOST:-0.0.0.0}"
MONITOR_PORT="${MONITOR_PORT:-8765}"

if [ -x "$VENV/bin/python" ]; then
  PY="$VENV/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo "❌ Python não encontrado (nem em $VENV nem no sistema)."
  exit 1
fi

CERT_DIR="$HERE/monitor/certs"
MONITOR_CERT="${MONITOR_CERT:-$CERT_DIR/monitor.crt}"
MONITOR_KEY="${MONITOR_KEY:-$CERT_DIR/monitor.key}"

if [ ! -f "$MONITOR_CERT" ] || [ ! -f "$MONITOR_KEY" ]; then
  echo "🔐 Gerando certificado autoassinado para $MONITOR_HOST (válido por 365 dias)..."
  mkdir -p "$CERT_DIR"
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -keyout "$MONITOR_KEY" -out "$MONITOR_CERT" \
    -subj "/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1,IP:::1,IP:0.0.0.0" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=critical,digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth" >/dev/null 2>&1
  chmod 600 "$MONITOR_KEY"
fi

MONITOR_PID=""
cleanup() {
  echo; echo "⏹️  Encerrando..."
  [ -n "$MONITOR_PID" ] && kill "$MONITOR_PID" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

echo "📊 Monitor: https://$MONITOR_HOST:$MONITOR_PORT  (certificado autoassinado: aceite o aviso do navegador)"
(cd "$HERE/monitor" && exec "$PY" -m uvicorn server:app --host "$MONITOR_HOST" --port "$MONITOR_PORT" --ssl-certfile "$MONITOR_CERT" --ssl-keyfile "$MONITOR_KEY" --log-level warning) &
MONITOR_PID=$!

cd "$HERE"
"$PY" run_mas.py "$@"
