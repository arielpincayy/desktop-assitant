"""Ejecutar: .venv/bin/python tests/claude_test.py"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import tools


class Result:
    returncode = 0
    stderr = ""
    stdout = (
        '{"type":"result","subtype":"success","is_error":false,'
        '"result":"Hola","session_id":"abc","total_cost_usd":0.01}\n'
    )


with patch.object(tools, "_claude_bin", return_value="/usr/bin/claude"), patch.object(
    tools.subprocess, "run", return_value=Result()
) as run:
    assert tools.ask_claude(
        "haz algo", directory=".", session_id="abc", model="sonnet"
    ) == {"response": "Hola", "session_id": "abc"}
    args, kwargs = run.call_args
    assert args[0] == [
        "/usr/bin/claude",
        "-p",
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        "--model",
        "sonnet",
        "--resume",
        "abc",
        "--",
        "haz algo",
    ], args[0]
    assert "input" not in kwargs


with patch.object(tools, "_claude_bin", return_value="/usr/bin/claude"), patch.object(
    tools.subprocess, "run", return_value=Result()
) as run:
    assert tools.ask_claude("haz algo") == {"response": "Hola", "session_id": "abc"}
    assert run.call_args.args[0] == [
        "/usr/bin/claude",
        "-p",
        "--output-format",
        "json",
        "--dangerously-skip-permissions",
        "--model",
        "sonnet",
        "--resume",
        "abc",
        "--",
        "haz algo",
    ], run.call_args.args[0]


class Fail(Result):
    returncode = 1
    stdout = (
        '{"type":"result","subtype":"error_during_execution","is_error":true,'
        '"result":"boom","session_id":"abc"}\n'
    )


with patch.object(tools, "_claude_bin", return_value="/usr/bin/claude"), patch.object(
    tools.subprocess, "run", return_value=Fail()
):
    assert tools.ask_claude("x") == {"error": "boom"}


class Invalid(Result):
    stdout = "no es json"
    stderr = "falló"


with patch.object(tools, "_claude_bin", return_value="/usr/bin/claude"), patch.object(
    tools.subprocess, "run", return_value=Invalid()
):
    assert tools.ask_claude("x") == {"error": "falló"}

with patch.object(tools, "_claude_bin", return_value=None):
    assert "error" in tools.ask_claude("x")

with patch.object(tools, "_claude_bin", return_value="/usr/bin/claude"):
    assert "error" in tools.ask_claude("x", directory="/no/existe")

print("ok")
