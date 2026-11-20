"""Ejecutar: .venv/bin/python tests/telegram_test.py"""

import asyncio
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import telegram_bot


def update(text="hola", user=1, chat=1):
    return {
        "update_id": 1,
        "message": {"from": {"id": user}, "chat": {"id": chat}, "text": text},
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


# Sin allowlist: responde el id y no toca al agente.
calls = []
with patch.object(telegram_bot, "ALLOWED", ""), patch.object(
    telegram_bot, "_call", lambda method, *a, **k: calls.append((method, k))
), patch.object(telegram_bot, "send_telegram", send):
    asyncio.run(telegram_bot.handle(update(), ask))
assert asked == [] and sent == []
assert calls[0][0] == "sendMessage" and calls[0][1]["chat_id"] == 1
assert "Tu id de Telegram es 1" in calls[0][1]["text"]

# Usuario no autorizado: silencio total.
calls.clear()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "_call", lambda method, *a, **k: calls.append(method)
), patch.object(telegram_bot, "send_telegram", send):
    asyncio.run(telegram_bot.handle(update(user=2, chat=2), ask))
assert asked == [] and sent == [] and calls == []

# Autorizado: avisa que escribe y responde.
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "_call", lambda method, *a, **k: calls.append(method)
), patch.object(telegram_bot, "send_telegram", send):
    asyncio.run(telegram_bot.handle(update(), ask))
assert asked == ["hola"] and sent == ["respuesta"]
assert calls[-1] == "sendChatAction"

# /start no llama al agente.
asked.clear()
sent.clear()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "send_telegram", send
):
    asyncio.run(telegram_bot.handle(update(text="/start"), ask))
assert asked == [] and sent == [telegram_bot.HELP]

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


sent.clear()
with patch.object(telegram_bot, "ALLOWED", "1"), patch.object(
    telegram_bot, "_call", lambda *a, **k: None
), patch.object(telegram_bot, "send_telegram", send):
    asyncio.run(telegram_bot.handle(update(), boom))
assert sent and "RuntimeError" in sent[0]

print("ok")
