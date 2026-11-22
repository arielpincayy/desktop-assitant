"""Ejecutar: .venv/bin/python tests/codex_test.py"""

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agent import tools


class Result:
    returncode = 0
    stderr = ""
    stdout = (
        '{"type":"thread.started","thread_id":"abc"}\n'
        '{"type":"turn.started"}\n'
        '{"type":"item.completed","item":{"id":"item_0","type":"agent_message","text":"Paso"}}\n'
        '{"type":"item.completed","item":{"id":"item_1","type":"agent_message","text":"Hola"}}\n'
        '{"type":"turn.completed","usage":{}}\n'
    )


with patch.object(tools, "_codex_bin", return_value="/usr/bin/codex"), patch.object(
    tools.subprocess, "run", return_value=Result()
) as run:
    assert tools.ask_codex(
        "haz algo", directory=".", session_id="abc", model="openai/x"
    ) == {"response": "Hola", "session_id": "abc"}
    args, kwargs = run.call_args
    assert args[0] == [
        "/usr/bin/codex",
        "exec",
        "resume",
        "--json",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--model",
        "openai/x",
        "abc",
        "-",
    ], args[0]
    assert kwargs["input"] == "haz algo"


with patch.object(tools, "_codex_bin", return_value="/usr/bin/codex"), patch.object(
    tools.subprocess, "run", return_value=Result()
) as run:
    assert tools.ask_codex("haz algo") == {"response": "Hola", "session_id": "abc"}
    assert run.call_args.args[0] == [
        "/usr/bin/codex",
        "exec",
        "resume",
        "--json",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--model",
        "openai/x",
        "abc",
        "-",
    ], run.call_args.args[0]


class Fail(Result):
    returncode = 1
    stdout = '{"type":"turn.failed","error":{"message":"boom"}}'


with patch.object(tools, "_codex_bin", return_value="/usr/bin/codex"), patch.object(
    tools.subprocess, "run", return_value=Fail()
):
    assert tools.ask_codex("x") == {"error": "boom"}

with patch.object(tools, "_codex_bin", return_value=None):
    assert "error" in tools.ask_codex("x")

with patch.object(tools, "_codex_bin", return_value="/usr/bin/codex"):
    assert "error" in tools.ask_codex("x", directory="/no/existe")

print("ok")
