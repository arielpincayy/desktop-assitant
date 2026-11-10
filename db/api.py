from contextlib import asynccontextmanager
import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import (
    Column, Integer, MetaData, Table, Text, create_engine, delete, event, func, insert, select, update,
)

DB_PATH = Path(os.getenv("DB_PATH", "/data/reminders.db"))

engine = create_engine(f"sqlite:///{DB_PATH}")


@event.listens_for(engine, "connect")
def _foreign_keys_on(dbapi_connection, _record) -> None:
    dbapi_connection.execute("PRAGMA foreign_keys = ON")


reminders = Table(
    "reminders",
    MetaData(),
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("description", Text),
    Column("remind_at", Text, nullable=False),
    Column("timezone", Text, nullable=False, server_default="America/Guayaquil"),
    Column("status", Text, nullable=False, server_default="pending"),
    Column("created_at", Text, nullable=False, server_default=func.current_timestamp()),
    Column("notified_at", Text),
    sqlite_autoincrement=True,
)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    reminders.metadata.create_all(engine)
    yield


app = FastAPI(title="Reminders API", lifespan=lifespan)


class ReminderCreate(BaseModel):
    user_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    remind_at: str = Field(min_length=1)
    timezone: str = "America/Guayaquil"
    status: str = "pending"


class ReminderPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    description: str | None = None
    remind_at: str | None = None
    timezone: str | None = None
    status: str | None = None
    notified_at: str | None = None


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Reminder not found")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/reminders")
def list_reminders(
    user_id: str | None = None,
    status: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, Any]]:
    query = select(reminders).order_by(reminders.c.id).limit(limit).offset(offset)
    if user_id is not None:
        query = query.where(reminders.c.user_id == user_id)
    if status is not None:
        query = query.where(reminders.c.status == status)
    with engine.connect() as connection:
        return [dict(row._mapping) for row in connection.execute(query)]


@app.get("/reminders/{reminder_id}")
def get_reminder(reminder_id: int) -> dict[str, Any]:
    with engine.connect() as connection:
        row = connection.execute(select(reminders).where(reminders.c.id == reminder_id)).first()
    if row is None:
        raise not_found()
    return dict(row._mapping)


@app.post("/reminders", status_code=201)
def create_reminder(reminder: ReminderCreate) -> dict[str, Any]:
    with engine.begin() as connection:
        row = connection.execute(
            insert(reminders).values(**reminder.model_dump()).returning(reminders)
        ).one()
    return dict(row._mapping)


@app.patch("/reminders/{reminder_id}")
def update_reminder(reminder_id: int, reminder: ReminderPatch) -> dict[str, Any]:
    changes = reminder.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")
    with engine.begin() as connection:
        row = connection.execute(
            update(reminders).where(reminders.c.id == reminder_id).values(**changes).returning(reminders)
        ).first()
    if row is None:
        raise not_found()
    return dict(row._mapping)


@app.delete("/reminders/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int) -> None:
    with engine.begin() as connection:
        result = connection.execute(delete(reminders).where(reminders.c.id == reminder_id))
    if result.rowcount == 0:
        raise not_found()
