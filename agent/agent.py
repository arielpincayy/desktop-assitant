
from datetime import datetime
from typing import AsyncGenerator
from zoneinfo import ZoneInfo

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import CONFIG
from agent.tools import REMINDER_TOOLS, ROOT

ULU_INSTRUCTION = "Eres ULU, asistente de recordatorios. Responde de forma clara, breve y en español."

class Agent:
    def __init__(self, name: str, instruction: str):
        self.name = name
        self.model = CONFIG.MODEL
        self.instruction = instruction
        self.session_service = InMemorySessionService()

    def _instruction(self, _ctx=None) -> str:
        now = datetime.now(ZoneInfo("America/Guayaquil")).strftime("%Y-%m-%d %H:%M (%A)")
        return (
            f"{self.instruction} Fecha y hora actual: {now}, zona America/Guayaquil; "
            "úsala para convertir lo que pida el usuario (fechas relativas, repeticiones) a una expresión cron de 5 campos: min hora díaMes mes díaSemana. "
            f"El código de este proyecto está en {ROOT}; las rutas relativas de list_dir, read_file y edit_file se resuelven contra esa carpeta. "
            "Usa list_dir para explorar carpetas, read_file para abrir un archivo y edit_file para reemplazar un fragmento exacto de texto; "
            "edit_file solo puede escribir archivos que el usuario pueda modificar sin sudo y no crea archivos nuevos. "
            "Usa copy_path, move_path y delete_path para copiar, mover o borrar archivos y carpetas; "
            "delete_path exige confirm=True y solo se usa cuando el usuario lo pida claramente. "
            "Usa compress_path para comprimir en .zip o .tar.gz. Ninguna de estas tools sobrescribe archivos existentes. "
            "Usa las herramientas para consultar y gestionar recordatorios. "
            "Si el usuario pide que al dispararse se ejecute un comando, usa action='command' y command con el comando exacto. "
            "Si pide que tú investigues o hagas algo al dispararse, usa action='agent' y pon la instrucción en description. "
            "Sin acción, action=null. "
            "Si pide usar OpenCode, Codex o Claude, delega con ask_opencode, ask_codex o ask_claude respectivamente; "
            "sin preferencia usa ask_opencode. Pásale la tarea completa y responde con su resultado. "
            "Las tools recuerdan en memoria la sesión y el modelo por proveedor y proyecto. "
            "Si pide listar sesiones, usa list_sessions y muéstrale las opciones; si elige una, pásala como session_id. "
            "Si pide una sesión nueva, usa reset_agent_session antes de delegar. "
            "Si pide un modelo, usa list_models si necesitas confirmar el identificador y pásalo como model; no inventes ids. "
            "Si el usuario no da el id, usa list_reminders para encontrarlo y pregunta si hay varias coincidencias. "
            "Solo opera sobre el usuario actual; elimina un recordatorio "
            "únicamente cuando el usuario lo solicite claramente."
        )

    def create_agent(self) -> LlmAgent:
        return LlmAgent(
            name=self.name,
            model=LiteLlm(model=self.model, extra_body={"thinking": {"type": "disabled"}}),
            instruction=self._instruction,
            tools=REMINDER_TOOLS,
        )

    async def create_session(self) -> None:
        session = await self.session_service.get_session(
            app_name=CONFIG.APP_NAME,
            user_id=CONFIG.USER_ID,
            session_id=CONFIG.SESSION_ID,
        )

        if session is None:
            await self.session_service.create_session(
                app_name=CONFIG.APP_NAME,
                user_id=CONFIG.USER_ID,
                session_id=CONFIG.SESSION_ID,
            )

    async def initialize(self) -> Runner:
        await self.create_session()
        runner = Runner(
            agent=self.create_agent(),
            app_name=CONFIG.APP_NAME,
            session_service=self.session_service,
        )
        return runner

    @staticmethod
    async def ask(question: str, agent: Runner) -> AsyncGenerator:
        response = ""
        async for event in agent.run_async(
            user_id=CONFIG.USER_ID,
            session_id=CONFIG.SESSION_ID,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=question)],
            ),
        ):
            if event.is_final_response() and event.content:
                response = event.content.parts[-1].text

        return response

    def __str__(self) -> str:
        return f"Agent(name={self.name}, model={self.model}, instruction={self.instruction})"
