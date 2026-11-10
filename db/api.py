from contextlib import asynccontextmanager

from fastapi import FastAPI

from .database import engine
from .models import reminders
from .routes import router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    reminders.metadata.create_all(engine)
    yield


app = FastAPI(title="Reminders API", lifespan=lifespan)


app.include_router(router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

