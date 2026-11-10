
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .config import DB_PATH
from .database import engine, metadata
from . import models
from .routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    metadata.create_all(engine)
    yield
    engine.dispose()

app = FastAPI(
    title="Reminders API",
    lifespan=lifespan,
)

app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}
