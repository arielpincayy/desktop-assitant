from pydantic import BaseModel, ConfigDict, Field

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