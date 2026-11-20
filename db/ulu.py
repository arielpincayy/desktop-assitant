import hashlib
import secrets

from fastapi import APIRouter
from pydantic import BaseModel, Field
from sqlalchemy import Column, Integer, Table, Text, insert, select, update

from .database import engine, metadata

DEFAULT_PASSWORD = "ulu"

ulu = Table(
    "ulu",
    metadata,
    Column("id", Integer, primary_key=True),  # fila única: id=1
    Column("telegram_salt", Text, nullable=False),
    Column("telegram_hash", Text, nullable=False),
)


def _scrypt(password: str, salt: bytes) -> str:
    return hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1).hex()


def hash_password(password: str) -> tuple[str, str]:
    """(sal, hash) en hex; sal aleatoria nueva en cada llamada."""
    salt = secrets.token_bytes(16)
    return salt.hex(), _scrypt(password, salt)


def verify_password(password: str, salt: str, hashed: str) -> bool:
    return secrets.compare_digest(_scrypt(password, bytes.fromhex(salt)), hashed)


def ensure_default(connection) -> None:
    if connection.execute(select(ulu.c.id)).first() is None:
        salt, hashed = hash_password(DEFAULT_PASSWORD)
        connection.execute(insert(ulu).values(id=1, telegram_salt=salt, telegram_hash=hashed))


def check_telegram_password(candidate: str) -> bool:
    with engine.connect() as connection:
        row = connection.execute(select(ulu.c.telegram_salt, ulu.c.telegram_hash)).first()
    return row is not None and verify_password(candidate, row.telegram_salt, row.telegram_hash)


router = APIRouter(prefix="/ulu", tags=["ULU"])


class PasswordIn(BaseModel):
    password: str = Field(min_length=1)


@router.put("/telegram-password", status_code=204)
def set_telegram_password(body: PasswordIn) -> None:
    salt, hashed = hash_password(body.password)
    with engine.begin() as connection:
        ensure_default(connection)
        connection.execute(update(ulu).where(ulu.c.id == 1).values(telegram_salt=salt, telegram_hash=hashed))
