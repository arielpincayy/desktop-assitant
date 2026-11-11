import subprocess
from pathlib import Path

from sqlalchemy import select

from .models import reminders

ROOT = Path(__file__).resolve().parents[1]
MARK = "# ulu-reminder"


def to_line(reminder_id: int, schedule: str) -> str:
    # ponytail: cron del sistema no tiene zona por línea: se asume la tz del sistema. Añadir CRON_TZ si hace falta.
    return f"{schedule} cd '{ROOT}' && .venv/bin/python recordar.py {reminder_id} {MARK}"


def sync(connection) -> None:
    """Reescribe las líneas ULU del crontab con los recordatorios pendientes."""
    rows = connection.execute(
        select(reminders.c.id, reminders.c.schedule).where(reminders.c.status == "pending").order_by(reminders.c.id)
    )
    cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True)
    kept = [l for l in (cur.stdout if cur.returncode == 0 else "").splitlines() if not l.endswith(MARK)]
    lines = kept + [to_line(r.id, r.schedule) for r in rows]
    subprocess.run(["crontab", "-"], input="\n".join(lines) + "\n", text=True, check=True)
