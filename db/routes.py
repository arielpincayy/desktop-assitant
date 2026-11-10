
from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from .database import engine
from .models import reminders
from .schemas import ReminderCreate, ReminderPatch
from sqlalchemy import delete, insert, select, update
from typing import Any


router = APIRouter(prefix="/reminders", tags=["Reminders"])

def not_found() -> HTTPException:
    return HTTPException(status_code=404, detail="Reminder not found")

@router.get("")
def list_reminders(
    user_id: str | None = None,
    status: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    query = select(reminders).order_by(reminders.c.id).limit(limit).offset(offset)

    if user_id is not None:
        query = query.where(reminders.c.user_id == user_id)

    if status is not None:
        query = query.where(reminders.c.status == status)

    with engine.connect() as connection:
        return [
            dict(row._mapping)
            for row in connection.execute(query)
        ]


@router.get("/{reminder_id}")
def get_reminder(reminder_id: int) -> dict[str, Any]:
    with engine.connect() as connection:
        row = connection.execute(select(reminders).where(reminders.c.id == reminder_id)).first()
    if row is None:
        raise not_found()
    return dict(row._mapping)


@router.post("", status_code=201)
def create_reminder(reminder: ReminderCreate) -> dict[str, Any]:
    with engine.begin() as connection:
        row = connection.execute(
            insert(reminders).values(**reminder.model_dump()).returning(reminders)
        ).one()
    return dict(row._mapping)


@router.patch("/{reminder_id}")
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


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int) -> None:
    with engine.begin() as connection:
        result = connection.execute(delete(reminders).where(reminders.c.id == reminder_id))
    if result.rowcount == 0:
        raise not_found()
