"""Uso: recordar.py <id> (cron) | recordar.py --pendientes (inicio de sesión).

Muestra la mascota con el recordatorio y guarda notified_at. --pendientes anuncia,
de uno en uno, los que cron no pudo disparar porque la PC estaba apagada.
"""

import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")  # antes de importar db: lee POSTGRES_PASSWORD
# cron y el autostart no traen el entorno gráfico completo
os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
os.environ.setdefault("WAYLAND_DISPLAY", "wayland-1")

# Idempotente: no hace nada si el contenedor ya está arriba; si no, lo levanta y espera.
subprocess.run(["docker", "compose", "up", "-d", "--wait", "db"], cwd=ROOT, check=True)

from sqlalchemy import select, update

from db.crontab import is_once, missed, sync
from db.database import engine
from db.models import reminders

SCRIPT = str(ROOT / "mostrar-mascota.sh")


def show(r, prefix: str = "") -> None:
    """Marca el recordatorio como anunciado y bloquea hasta que se cierra la mascota."""
    changes = {"notified_at": datetime.now(timezone.utc).isoformat()}
    if is_once(r.schedule):
        changes["status"] = "announced"  # no se repite: sale del crontab y de la lista principal
    with engine.begin() as c:
        c.execute(update(reminders).where(reminders.c.id == r.id).values(**changes))
        if "status" in changes:
            sync(c)
    msg = prefix + (f"{r.title}\n{r.description}" if r.description else r.title)
    subprocess.run([SCRIPT, "--mensaje", msg])


def aware(ts: str) -> datetime:
    d = datetime.fromisoformat(ts)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def pendientes() -> None:
    now = datetime.now(timezone.utc)
    with engine.connect() as c:
        rows = c.execute(select(reminders).where(reminders.c.status == "pending")).all()
    perdidos = []
    for r in rows:
        due = missed(r.schedule, r.timezone, aware(r.notified_at or r.created_at), now)
        if due:
            perdidos.append((due, r))
    for due, r in sorted(perdidos, key=lambda x: x[0]):
        show(r, f"Pendiente de las {due:%H:%M} — ")


if sys.argv[1] == "--pendientes":
    pendientes()
else:
    with engine.connect() as c:
        r = c.execute(select(reminders).where(reminders.c.id == int(sys.argv[1]))).first()
    if r is not None and r.status == "pending":
        show(r)
