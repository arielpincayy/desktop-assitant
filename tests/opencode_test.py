"""Ejecutar: .venv/bin/python tests/opencode_test.py"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import tools


class Result:
    returncode = 0
    stderr = ""
    stdout = (
        '{"type":"step_start","sessionID":"ses_1","part":{}}\n'
        '{"type":"text","sessionID":"ses_1","part":{"text":"Hola"}}\n'
    )


with patch.object(tools, "_opencode_bin", return_value="/usr/bin/opencode"), patch.object(
    tools.subprocess, "run", return_value=Result()
) as run:
    assert tools.ask_opencode(
        "haz algo", directory=".", session_id="ses_1", model="opencode/x"
    ) == {"response": "Hola", "session_id": "ses_1"}
    args, kwargs = run.call_args
    assert args[0] == [
        "/usr/bin/opencode",
        "run",
        "--format",
        "json",
        "--auto",
        "--archived",
        "--session",
        "ses_1",
        "--model",
        "opencode/x",
    ], args[0]
    assert kwargs["input"] == "haz algo"


class Fail(Result):
    returncode = 1
    stdout = '{"type":"error","sessionID":"","error":{"message":"boom"}}'


with patch.object(tools, "_opencode_bin", return_value="/usr/bin/opencode"), patch.object(
    tools.subprocess, "run", return_value=Fail()
):
    assert tools.ask_opencode("x") == {"error": "boom"}

with patch.object(tools, "_opencode_bin", return_value=None):
    assert "error" in tools.ask_opencode("x")

with patch.object(tools, "_opencode_bin", return_value="/usr/bin/opencode"):
    assert "error" in tools.ask_opencode("x", directory="/no/existe")

print("ok")
