"""Ejecutar: .venv/bin/python tests/acciones_test.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from pydantic import ValidationError

from acciones import run_command
from db.schemas import ReminderCreate

assert run_command("printf hola") == "hola"
assert run_command("echo boom >&2; exit 1") == "boom"
assert "límite" in run_command("sleep 5", timeout=0.2)

base = {"user_id": "u", "title": "t", "schedule": "0 9 * * *"}
assert ReminderCreate(**base).action is None
assert ReminderCreate(**base, action="agent").action == "agent"
assert ReminderCreate(**base, action="command", command=" echo hola ").command == "echo hola"
for kwargs in ({"action": "command"}, {"action": "agent", "command": "echo hola"}):
    try:
        ReminderCreate(**base, **kwargs)
    except ValidationError:
        pass
    else:
        raise AssertionError(f"debería fallar: {kwargs}")
print("ok")
