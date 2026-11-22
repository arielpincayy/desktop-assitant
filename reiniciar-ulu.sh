#!/bin/sh
# Reinicia ULU completo sin borrar la base de datos.
# Uso: ./reiniciar-ulu.sh
set -u
cd "$(dirname "$0")"
ROOT=$(pwd -P)
[ -f .env ] && { set -a; . ./.env; set +a; }
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/ulu/api.log"
mkdir -p "$(dirname "$LOG")"

stop() {
  pattern=$1
  for pid in $(pgrep -f "$pattern" 2>/dev/null); do
    [ "$(readlink -f "/proc/$pid/cwd" 2>/dev/null)" = "$ROOT" ] || continue
    kill "$pid" 2>/dev/null || true
  done
}

echo "ULU: deteniendo API/agente y bot..."
stop '\.venv/bin/python main\.py'
stop 'telegram_bot\.py'
sleep 1

echo "ULU: reiniciando Postgres y SearXNG..."
docker compose restart db >>"$LOG" 2>&1 || docker compose up -d --wait db >>"$LOG" 2>&1 || {
  echo "ULU: no se pudo reiniciar Postgres (ver $LOG)." >&2
  exit 1
}
docker compose restart searxng >>"$LOG" 2>&1 || docker compose up -d searxng >>"$LOG" 2>&1 || true

echo "ULU: iniciando API/agente..."
./ulu-api.sh || exit 1

if [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
  echo "ULU: iniciando bot de Telegram..."
  nohup ./ulu-telegram.sh >/dev/null 2>&1 &
fi

echo "ULU: listo. Cierra y reabre la ventana de recordatorios para cargar cambios de UI."
