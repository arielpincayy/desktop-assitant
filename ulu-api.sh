#!/bin/sh
# Asegura Postgres y la API/agente de ULU (idempotente). Log: ~/.local/state/ulu/api.log
set -u
cd "$(dirname "$0")"

[ -f .env ] && { set -a; . ./.env; set +a; }
API="${REMINDERS_API_URL:-http://localhost:8001}"
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/ulu/api.log"
mkdir -p "$(dirname "$LOG")"
healthy() { curl -fs -m 2 "$API/health" >/dev/null 2>&1; }

healthy && exit 0

# La API la crea si falta: primero la base de datos.
docker compose up -d --wait db >>"$LOG" 2>&1 || {
  echo "ULU: no se pudo iniciar Postgres (ver $LOG)." >&2
  exit 1
}
docker compose up -d searxng >>"$LOG" 2>&1 || true  # la búsqueda web es opcional
nohup .venv/bin/python main.py >>"$LOG" 2>&1 &
pid=$!
for _ in $(seq 40); do
  healthy && exit 0
  kill -0 "$pid" 2>/dev/null || {
    echo "ULU: la API/agente se detuvo al iniciar (ver $LOG)." >&2
    exit 1
  }
  sleep 0.5
done
echo "ULU: la API/agente no respondió a tiempo (ver $LOG)." >&2
exit 1
