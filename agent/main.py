"""Ejecuta una pregunta fija con un modelo compatible con LiteLLM."""

import asyncio
import os
from pathlib import Path
import subprocess

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types


APP_NAME = "agente_demo"
USER_ID = "usuario"
SESSION_ID = "sesion_demo"
QUESTION = "hola amigazo, cuentame un chiste corto y divertido en español, por favor."


async def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    load_dotenv(project_root / ".env")

    model = "openai/" + os.getenv("AGENT_MODEL", "deepseek-v4.1-flash")

    agent = LlmAgent(
        name="agente_preguntas",
        model=LiteLlm(model=model),
        instruction="Responde de forma clara, breve y en español.",
    )

    session_service = InMemorySessionService()
    await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
    )
    
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=QUESTION)],
        ),
    ):
        if event.is_final_response() and event.content:
            answer = event.content.parts[-1].text
            if answer:
                mascot = project_root / "mostrar-mascota.sh"
                subprocess.Popen(
                    [str(mascot), "--mensaje", answer],
                    cwd=project_root,
                )


if __name__ == "__main__":
    asyncio.run(main())
