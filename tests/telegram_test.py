"""Ejecutar: .venv/bin/python tests/telegram_test.py"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import telegram_bot


def update(text="hola", user=1, chat=1):
    return {
        "update_id": 1,
        "message": {
            "message_id": 10,
            "from": {"id": user},
            "chat": {"id": chat},
            "text": text,
        },
    }


assert telegram_bot.chunk("a" * 10, 4) == ["aaaa", "aaaa", "aa"]
assert telegram_bot.chunk("1234567\nabc", 8) == ["1234567", "abc"]
assert telegram_bot.chunk("", 8) == []
assert telegram_bot.chunk("corto", 8) == ["corto"]

asked = []


async def ask(text):
    asked.append(text)
    return "respuesta"


sent = []


def send(text):
    sent.append(text)
    return True


calls = []


def record(method, *args, **kwargs):
    calls.append((method, kwargs))
    return {"ok": True}


def reset(unlocked=False):
    asked.clear()
    sent.clear()
    calls.clear()
    telegram_bot.unlocked = unlocked


# Sin allowlist: responde el id y no toca al agente.
reset()
with patch.object(telegram_bot, "ALLOWED", ""), patch.object(
    telegram_bot, "_call", record
), patch.object(telegram_bot, "send_telegram", send):
    asyncio.run(telegram_bot.handle(update(), ask))
assert asked == [] and sent == []
assert calls[0][0] == "sendMessage" and calls[0][1]["chat_id"] == 1
assert "Tu id de Telegram es 1" in calls[0][1]["text"]

# Usuario no autorizado: ni siquiera se le pide la clave.
reset()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", lambda c: c == "secreta"
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(text="/clave secreta", user=2, chat=2), ask))
assert asked == [] and sent == [] and calls == []

# DB caída: no se puede verificar la clave y el chat sigue bloqueado.
def boom_db(_c):
    raise RuntimeError("db")


reset()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", boom_db
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(text="/clave x"), ask))
assert asked == [] and "No pude verificar" in sent[0] and telegram_bot.unlocked is False

# Bloqueado: pide la clave y no llama al agente.
reset()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", lambda c: c == "secreta"
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(), ask))
assert asked == [] and "clave" in sent[0]

# Clave incorrecta: borra el mensaje, avisa y no llama al agente.
reset()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", lambda c: c == "secreta"
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
), patch.object(telegram_bot.asyncio, "sleep", AsyncMock()):
    asyncio.run(telegram_bot.handle(update(text="/clave nope"), ask))
assert asked == [] and sent == ["Contraseña incorrecta."]
assert telegram_bot.unlocked is False
assert calls[0][0] == "deleteMessage" and calls[0][1]["message_id"] == 10

# Clave correcta: desbloquea; el mensaje de la clave no llega al agente.
reset()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", lambda c: c == "secreta"
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(text="/clave secreta"), ask))
assert asked == [] and sent == ["Acceso concedido."]
assert telegram_bot.unlocked is True
assert calls[0][0] == "deleteMessage"

# Ya desbloqueado: un mensaje normal llega al agente.
asked.clear()
sent.clear()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", lambda c: c == "secreta"
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(), ask))
assert asked == ["hola"] and sent == ["respuesta"]

# /clave repetido no se reenvía al agente; /start muestra la ayuda.
asked.clear()
sent.clear()
telegram_bot.unlocked = True
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", lambda c: c == "secreta"
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(text="/clave secreta"), ask))
    asyncio.run(telegram_bot.handle(update(text="/start"), ask))
assert asked == [] and sent == ["Ya tienes acceso.", telegram_bot.HELP]

# /salir vuelve a bloquear.
asked.clear()
sent.clear()
telegram_bot.unlocked = True
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", lambda c: c == "secreta"
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(text="/salir"), ask))
assert asked == [] and sent == ["Sesión bloqueada."]
assert telegram_bot.unlocked is False

# Sin configuración no envía; un fallo de red no propaga excepciones.
with patch.object(telegram_bot, "TOKEN", ""):
    assert telegram_bot.send_telegram("x") is False
with patch.object(
    telegram_bot.requests, "post", side_effect=telegram_bot.requests.ConnectionError()
):
    assert telegram_bot._call("sendMessage", chat_id=1, text="x") is None


# Un error del agente se responde sin tumbar el bot.
async def boom(_text):
    raise RuntimeError("boom")


reset(unlocked=True)
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "check_password", lambda c: c == "secreta"
), patch.object(telegram_bot, "_call", record), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(), boom))
assert sent and "RuntimeError" in sent[0]

print("ok")
