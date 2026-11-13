#!/bin/sh
# Abre ULU: antes se asegura de que Postgres (docker) y la API/agente (main.py) estén arriba.
set -u
cd "$(dirname "$0")"

[ -f .env ] && { set -a; . ./.env; set +a; }
API="${REMINDERS_API_URL:-http://localhost:8001}"
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/ulu/api.log"
mkdir -p "$(dirname "$LOG")"

fail() {
  echo "ULU: $1" >&2
  notify-send -u critical -i "$PWD/assets/fantasmita.svg" "ULU" "$1" 2>/dev/null || true
  exit 1
}
healthy() { curl -fs -m 2 "$API/health" >/dev/null 2>&1; }

if ! healthy; then
  # La API la crea si falta: primero la base de datos.
  docker compose up -d --wait db >>"$LOG" 2>&1 || fail "No se pudo iniciar el contenedor de la base de datos (ver $LOG)."
  docker compose up -d searxng >>"$LOG" 2>&1 || true  # la búsqueda web es opcional
  nohup .venv/bin/python main.py >>"$LOG" 2>&1 &
  pid=$!
  for _ in $(seq 40); do
    healthy && break
    kill -0 "$pid" 2>/dev/null || fail "La API/agente se detuvo al iniciar (ver $LOG)."
    sleep 0.5
  done
  healthy || fail "La API/agente no respondió a tiempo (ver $LOG)."
fi

exec /usr/bin/python3 recordatorios.py "$@"
