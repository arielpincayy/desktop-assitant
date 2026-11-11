"""Ejecutar: .venv/bin/python tests/crontab_test.py"""

import os
import sys

os.environ.setdefault("POSTGRES_PASSWORD", "x")  # db.config la exige al importar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from datetime import datetime, timezone

from db.crontab import MARK, missed, to_line

line = to_line(7, "30 8 * * 1,3")
assert line.startswith("30 8 * * 1,3 "), line
assert "recordar.py 7" in line and line.endswith(MARK), line
now = datetime(2026, 11, 10, 17, 0, tzinfo=timezone.utc)  # 12:00 en Guayaquil
due = missed("0 9 * * *", "America/Guayaquil", datetime(2026, 11, 9, 15, 0, tzinfo=timezone.utc), now)
assert due and (due.month, due.day, due.hour) == (11, 10, 9), due
assert missed("0 9 * * *", "America/Guayaquil", datetime(2026, 11, 10, 14, 30, tzinfo=timezone.utc), now) is None
print("ok")
