#!/bin/sh
# Abre ULU: antes se asegura de que Postgres (docker) y la API/agente (main.py) estén arriba.
set -u
cd "$(dirname "$0")"

[ -f .env ] && { set -a; . ./.env; set +a; }  # recordatorios.py lee REMINDERS_API_URL
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/ulu/api.log"

fail() {
  echo "ULU: $1" >&2
  notify-send -u critical -i "$PWD/assets/fantasmita.svg" "ULU" "$1" 2>/dev/null || true
  exit 1
}

./ulu-api.sh || fail "No se pudo iniciar la base de datos o la API/agente (ver $LOG)."

exec /usr/bin/python3 recordatorios.py "$@"
