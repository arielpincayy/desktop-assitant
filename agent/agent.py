
from typing import AsyncGenerator

from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import CONFIG

class Agent:
    def __init__(self, name: str, instruction: str):
        self.name = name
        self.model = CONFIG.MODEL
        self.instruction = instruction
        self.session_service = InMemorySessionService()

    def create_agent(self) -> LlmAgent:
        return LlmAgent(
            name=self.name,
            model=LiteLlm(model=self.model),
            instruction=self.instruction,
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
