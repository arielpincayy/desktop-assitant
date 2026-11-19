
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from croniter import croniter
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import delete, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from . import crontab
from .database import engine
from .models import comandos, reminders
from .schemas import ReminderCreate, ReminderPatch


router = APIRouter(prefix="/reminders", tags=["Reminders"])

def _out(row, command: str | None = None) -> dict[str, Any]:
    """Fila + next_run (ISO con offset): próxima ejecución según el cron."""
    d = dict(row._mapping)
    d.setdefault("command", command)
    try:
        base = datetime.now(ZoneInfo(d["timezone"]))
        d["next_run"] = croniter(d["schedule"], base).get_next(datetime).isoformat()
    except Exception:
        d["next_run"] = None
    return d


def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Reminder not found")

@router.get("")
def list_reminders(
    user_id: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    query = (
        select(reminders, comandos.c.command)
        .outerjoin(comandos, comandos.c.reminder_id == reminders.c.id)
        .order_by(reminders.c.id)
        .limit(limit)
        .offset(offset)
    )

    if user_id is not None:
        query = query.where(reminders.c.user_id == user_id)

    if status is not None:
        query = query.where(reminders.c.status == status)

    with engine.connect() as connection:
        return [
            _out(row)
            for row in connection.execute(query)
        ]


@router.get("/{reminder_id}")
def get_reminder(reminder_id: int) -> dict[str, Any]:
    with engine.connect() as connection:
        row = connection.execute(
            select(reminders, comandos.c.command)
            .outerjoin(comandos, comandos.c.reminder_id == reminders.c.id)
            .where(reminders.c.id == reminder_id)
        ).first()
    if row is None:
        raise not_found()
    return _out(row)


@router.post("", status_code=201)
def create_reminder(reminder: ReminderCreate) -> dict[str, Any]:
    data = reminder.model_dump(exclude={"command"})
    command = reminder.command if reminder.action == "command" else None
    with engine.begin() as connection:
        # Borrado perezoso: anunciados con más de 5 días.
        # ponytail: compara texto; vale porque recordar.py guarda notified_at como ISO UTC.
        limit = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        connection.execute(delete(reminders).where(reminders.c.status == "announced", reminders.c.notified_at < limit))
        row = connection.execute(
            insert(reminders).values(**data).returning(reminders)
        ).one()
        if command:
            connection.execute(
                insert(comandos).values(reminder_id=row.id, command=command)
            )
        crontab.sync(connection)
    return _out(row, command)


@router.patch("/{reminder_id}")
def update_reminder(reminder_id: int, reminder: ReminderPatch) -> dict[str, Any]:
    changes = reminder.model_dump(exclude_unset=True)
    has_command = "command" in changes
    command = changes.pop("command", None)
    if not changes and not has_command:
        raise HTTPException(status_code=400, detail="No fields to update")
    with engine.begin() as connection:
        current = connection.execute(
            select(reminders.c.status, reminders.c.action).where(reminders.c.id == reminder_id)
        ).first()
        if current is None:
            raise not_found()
        if current.status == "announced":
            raise HTTPException(status_code=409, detail="Announced reminders cannot be modified")

        final_action = changes["action"] if "action" in changes else current.action
        if final_action == "command":
            if has_command:
                if not command:
                    raise HTTPException(status_code=400, detail="command es obligatorio cuando action='command'")
            else:
                command = connection.execute(
                    select(comandos.c.command).where(comandos.c.reminder_id == reminder_id)
                ).scalar()
                if not command:
                    raise HTTPException(status_code=400, detail="command es obligatorio cuando action='command'")
        else:
            if has_command and command is not None:
                raise HTTPException(status_code=400, detail="command solo se usa cuando action='command'")
            command = None

        row = None
        if changes:
            row = connection.execute(
                update(reminders).where(reminders.c.id == reminder_id).values(**changes).returning(reminders)
            ).first()
        if row is None:
            row = connection.execute(
                select(reminders).where(reminders.c.id == reminder_id)
            ).first()
        if row is None:
            raise not_found()

        if final_action == "command":
            connection.execute(
                pg_insert(comandos)
                .values(reminder_id=reminder_id, command=command)
                .on_conflict_do_update(
                    index_elements=[comandos.c.reminder_id],
                    set_={"command": command},
                )
            )
        else:
            connection.execute(delete(comandos).where(comandos.c.reminder_id == reminder_id))

        crontab.sync(connection)
    return _out(row, command)


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int) -> None:
    with engine.begin() as connection:
        result = connection.execute(delete(reminders).where(reminders.c.id == reminder_id))
        crontab.sync(connection)
    if result.rowcount == 0:
        raise not_found()
