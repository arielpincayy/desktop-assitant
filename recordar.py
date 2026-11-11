"""Uso: recordar.py <id>. Lo invoca cron: muestra la mascota con el recordatorio."""

import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")  # antes de importar db: lee POSTGRES_PASSWORD
# cron no trae entorno gráfico
os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
os.environ.setdefault("WAYLAND_DISPLAY", "wayland-1")

# Idempotente: no hace nada si el contenedor ya está arriba; si no, lo levanta y espera.
subprocess.run(["docker", "compose", "up", "-d", "--wait", "db"], cwd=ROOT, check=True)

from sqlalchemy import select

from db.database import engine
from db.models import reminders

with engine.connect() as c:
    r = c.execute(select(reminders).where(reminders.c.id == int(sys.argv[1]))).first()
if r is None or r.status != "pending":
    sys.exit(0)

msg = f"{r.title}\n{r.description}" if r.description else r.title
script = str(ROOT / "mostrar-mascota.sh")
os.execv(script, [script, "--mensaje", msg])
