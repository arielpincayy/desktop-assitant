
from sqlalchemy import create_engine, event, MetaData

from .config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}")
metadata = MetaData()

@event.listens_for(engine, "connect")
def enable_foreign_keys(connection, _record):
    connection.execute("PRAGMA foreign_keys = ON")
