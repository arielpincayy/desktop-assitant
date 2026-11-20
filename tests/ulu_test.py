"""Ejecutar: .venv/bin/python tests/ulu_test.py"""

import os
import sys

os.environ.setdefault("POSTGRES_PASSWORD", "x")  # db.config la exige al importar
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from db.ulu import hash_password, verify_password

s1, h1 = hash_password("ulu")
s2, h2 = hash_password("ulu")
assert s1 != s2 and h1 != h2  # sal distinta en cada hash
assert verify_password("ulu", s1, h1)
assert not verify_password("otra", s1, h1)
assert "ulu" not in h1

print("ok")
