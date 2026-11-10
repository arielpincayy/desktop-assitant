import os
from pathlib import Path

DB_PATH = Path(os.getenv("DB_PATH", "/data/reminders.db"))