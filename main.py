"""Ejecuta una pregunta fija con un modelo compatible con LiteLLM."""

import asyncio
from pathlib import Path
import subprocess
from dotenv import load_dotenv

from agent.agent import Agent

QUESTION = "hola amigazo, cuentame un chiste corto y divertido en español, por favor."

load_dotenv(".env")

def mascot_say(message: str) -> None:
    """Muestra un mensaje en la mascota."""
    subprocess.Popen(["./mostrar-mascota.sh", "--mensaje", message])


async def main() -> None:

    agent = await Agent(
        name="agente_preguntas",
        instruction="Responde de forma clara, breve y en español.",
    ).initialize()

    response = await Agent.ask(QUESTION, agent)
    if response: mascot_say(response)


if __name__ == "__main__":
    asyncio.run(main())
