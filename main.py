"""Levanta la API de recordatorios y el chat con ULU (uvicorn)."""

import asyncio
import os
import threading
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv(".env")  # antes de importar db: db/config.py lee POSTGRES_PASSWORD al importar

import uvicorn
from pydantic import BaseModel, Field

from agent.agent import Agent
from db.api import app

API_URL = os.getenv("REMINDERS_API_URL", "http://localhost:8001")

# Las tools hacen requests síncronos contra esta misma API: el agente corre en su
# propio loop/hilo para no bloquear el loop de uvicorn.
# ponytail: un solo hilo y una sesión global; chats concurrentes se serializan.
loop = asyncio.new_event_loop()
threading.Thread(target=loop.run_forever, daemon=True).start()
runner = asyncio.run_coroutine_threadsafe(
    Agent(
        name="ulu",
        instruction="Eres ULU, asistente de recordatorios. Responde de forma clara, breve y en español.",
    ).initialize(),
    loop,
).result()


class ChatIn(BaseModel):
    message: str = Field(min_length=1)


@app.post("/chat")
def chat(body: ChatIn) -> dict[str, str]:
    reply = asyncio.run_coroutine_threadsafe(Agent.ask(body.message, runner), loop).result()
    return {"reply": reply or "No tengo respuesta."}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=urlparse(API_URL).port or 8001)
