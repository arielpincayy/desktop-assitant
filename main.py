"""Ejecuta una pregunta fija con un modelo compatible con LiteLLM."""

import asyncio
import subprocess
from dotenv import load_dotenv
import sys

from agent.agent import Agent

QUESTION = "Hola!"

if len(sys.argv) > 1:
    QUESTION = sys.argv[1]

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
