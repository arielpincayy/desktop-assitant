"""Ejecutar: .venv/bin/python tests/crontab_test.py"""

import os
import sys

os.environ.setdefault("POSTGRES_PASSWORD", "x")  # db.config la exige al importar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from db.crontab import MARK, to_line

line = to_line(7, "30 8 * * 1,3")
assert line.startswith("30 8 * * 1,3 "), line
assert "recordar.py 7" in line and line.endswith(MARK), line
print("ok")
