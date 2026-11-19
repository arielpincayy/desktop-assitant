"""Acciones que ejecuta un recordatorio al dispararse."""

import asyncio
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COMMAND_TIMEOUT = 30
AGENT_TIMEOUT = 120
MAX_OUTPUT = 4000


def _clip(text: str) -> str:
    # shortcut: recorta a 4000 caracteres para no reventar argv; subir si hace falta ver más.
    text = text.replace("\x00", "")
    return text if len(text) <= MAX_OUTPUT else text[:MAX_OUTPUT] + "\n…"


def run_command(command: str, timeout: float = COMMAND_TIMEOUT) -> str:
    """Ejecuta un comando de shell y devuelve su salida (stdout + stderr)."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=ROOT,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return f"El comando superó el límite de {timeout:g} s."
    except Exception as exc:
        return f"No se pudo ejecutar el comando: {exc}"
    parts = [part.strip() for part in (result.stdout, result.stderr) if part.strip()]
    if parts:
        return _clip("\n".join(parts))
    if result.returncode:
        return f"El comando terminó con código {result.returncode}."
    return "(sin salida)"


def ask_agent(prompt: str, timeout: float = AGENT_TIMEOUT) -> str:
    """Pide al agente ULU que ejecute una instrucción y devuelve su respuesta."""
    from agent.agent import Agent, ULU_INSTRUCTION

    async def _ask() -> str:
        agent = Agent(name="ulu", instruction=ULU_INSTRUCTION)
        runner = await agent.initialize()
        return await asyncio.wait_for(Agent.ask(prompt, runner), timeout=timeout)

    try:
        return _clip(asyncio.run(_ask()) or "(sin respuesta)")
    except Exception as exc:
        return f"No se pudo ejecutar al agente: {exc}"
