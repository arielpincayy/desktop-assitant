from typing import Literal

from croniter import croniter
from pydantic import BaseModel, ConfigDict, Field, field_validator


def _check_cron(v: str | None) -> str | None:
    if v is not None and (len(v.split()) != 6 or not croniter.is_valid(v, second_at_beginning=True)):
        raise ValueError("schedule debe ser cron de 6 campos: seg min hora díaMes mes díaSemana")
    return v

class ReminderCreate(BaseModel):
    user_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    description: str | None = None
    schedule: str = Field(min_length=1)
    timezone: str = "America/Guayaquil"
    status: Literal["pending", "done"] = "pending"

    _v = field_validator("schedule")(_check_cron)


class ReminderPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    description: str | None = None
    schedule: str | None = None
    timezone: str | None = None
    status: Literal["pending", "done"] | None = None
    notified_at: str | None = None

    _v = field_validator("schedule")(_check_cron)