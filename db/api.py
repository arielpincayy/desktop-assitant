from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

from . import crontab
from .database import engine
from .models import reminders
from .routes import router

@asynccontextmanager
async def lifespan(_app: FastAPI):
    reminders.metadata.create_all(engine)
    with engine.begin() as connection:
        # migración única: quita los segundos de los cron antiguos de 6 campos
        connection.execute(text(
            r"UPDATE reminders SET schedule = regexp_replace(trim(schedule), '^\S+\s+', '') "
            r"WHERE array_length(regexp_split_to_array(trim(schedule), '\s+'), 1) = 6"
        ))
        crontab.sync(connection)  # recordatorios ya existentes
    yield


app = FastAPI(title="Reminders API", lifespan=lifespan)


app.include_router(router)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

