#!/bin/sh
# Arranca el bot de Telegram de ULU y la API que usan sus tools.
set -u
cd "$(dirname "$0")"
[ -f .env ] && { set -a; . ./.env; set +a; }
[ -n "${TELEGRAM_BOT_TOKEN:-}" ] || exit 0  # sin bot configurado, el autostart no hace nada
./ulu-api.sh || exit 1  # sin API, las tools de recordatorios fallan
LOG="${XDG_STATE_HOME:-$HOME/.local/state}/ulu/telegram.log"
mkdir -p "$(dirname "$LOG")"
exec flock -n "$LOG.lock" .venv/bin/python telegram_bot.py >>"$LOG" 2>&1
