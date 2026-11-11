from sqlalchemy import (
    Column, Integer, Table, Text, func
)
from .database import metadata

reminders = Table(
    "reminders",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("user_id", Text, nullable=False),
    Column("title", Text, nullable=False),
    Column("description", Text),
    # Cron de 5 campos: "min hora díaMes mes díaSemana"
    Column("schedule", Text, nullable=False),
    Column("timezone", Text, nullable=False, server_default="America/Guayaquil"),
    Column("status", Text, nullable=False, server_default="pending"),
    Column("created_at", Text, nullable=False, server_default=func.current_timestamp()),
    Column("notified_at", Text),
)