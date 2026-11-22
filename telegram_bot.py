"""Chat de ULU por Telegram (long polling) y envío de avisos.

Uso: ./ulu-telegram.sh

Solo responde a TELEGRAM_ALLOWED_USER_ID y pide /clave tras cada arranque: sus
herramientas incluyen recordatorios con shell, ask_opencode --auto, ask_codex sin
sandbox y ask_claude sin confirmaciones, que ejecutan código en esta PC.
"""

import asyncio
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
ALLOWED = os.getenv("TELEGRAM_ALLOWED_USER_ID", "").strip()
API = f"https://api.telegram.org/bot{TOKEN}"
POLL_TIMEOUT = 25
MAX_LENGTH = 4000
HELP = (
    "Soy ULU, tu asistente. Pídeme crear, consultar, editar o borrar recordatorios, "
    "buscar en la web o delegar una tarea de código. Envía /salir para bloquear el chat."
)
unlocked = False


def _call(method: str, http_timeout: float = 5, **params):
    """Llama a la Bot API y devuelve `result`, o None si falla. Nunca loguea el token."""
    try:
        response = requests.post(f"{API}/{method}", json=params, timeout=http_timeout)
        body = response.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"Telegram: {method}: {type(exc).__name__}", file=sys.stderr)
        return None
    if not body.get("ok"):
        print(f"Telegram: {method}: {body.get('description', 'error')}", file=sys.stderr)
        return None
    return body.get("result")


def check_password(candidate: str) -> bool:
    """Verifica la clave contra la tabla `ulu` (hash con sal). Import perezoso: db/config.py exige el .env."""
    from db.ulu import check_telegram_password

    return check_telegram_password(candidate)


def chunk(text: str, limit: int = MAX_LENGTH) -> list[str]:
    """Trocea el texto en mensajes de Telegram sin partir líneas si se puede."""
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut <= 0:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    if text:
        parts.append(text)
    return parts


def send_telegram(text: str) -> bool:
    """Envía texto al chat permitido. Sin configurar o si falla, no rompe al llamante."""
    if not TOKEN or not ALLOWED:
        return False
    ok = True
    for part in chunk(text):
        ok = _call("sendMessage", chat_id=ALLOWED, text=part) is not None and ok
    return ok


async def handle(update: dict, ask) -> None:
    global unlocked
    message = update.get("message") or {}
    sender = (message.get("from") or {}).get("id")
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return
    if not ALLOWED:
        _call(
            "sendMessage",
            chat_id=chat_id,
            text=f"Tu id de Telegram es {sender}. Ponlo en TELEGRAM_ALLOWED_USER_ID y reinicia el bot.",
        )
        return
    if str(sender) != ALLOWED:
        return
    text = (message.get("text") or "").strip()
    if not text:
        return
    if text == "/clave" or text.startswith("/clave "):
        if message.get("message_id"):
            _call("deleteMessage", chat_id=chat_id, message_id=message["message_id"])
        candidate = text.partition(" ")[2].strip()
        if unlocked:
            send_telegram("Ya tienes acceso.")
        elif not candidate:
            send_telegram("Uso: /clave <contraseña>.")
        else:
            try:
                ok = await asyncio.to_thread(check_password, candidate)
            except Exception as exc:
                print(f"Telegram: clave: {type(exc).__name__}", file=sys.stderr)
                send_telegram("No pude verificar la clave (¿Postgres está arriba?).")
                return
            if ok:
                unlocked = True
                send_telegram("Acceso concedido.")
            else:
                await asyncio.sleep(2)
                send_telegram("Contraseña incorrecta.")
        return
    if not unlocked:
        send_telegram("Envía /clave <contraseña> para usar ULU.")
        return
    if text == "/salir":
        unlocked = False
        send_telegram("Sesión bloqueada.")
        return
    if text == "/start":
        send_telegram(HELP)
        return
    _call("sendChatAction", chat_id=chat_id, action="typing")
    try:
        answer = await ask(text)
    except Exception as exc:
        print(f"Telegram: agente: {type(exc).__name__}: {exc}", file=sys.stderr)
        answer = f"No pude responder ({type(exc).__name__}). Revisa el log del bot."
    send_telegram(answer or "No tengo respuesta.")


async def serve() -> None:
    from agent.agent import Agent, ULU_INSTRUCTION

    runner = await Agent(name="ulu", instruction=ULU_INSTRUCTION).initialize()

    async def ask(text: str) -> str:
        return await Agent.ask(text, runner)

    offset = 0
    print("Telegram: escuchando", file=sys.stderr)
    while True:
        batch = await asyncio.to_thread(
            _call,
            "getUpdates",
            http_timeout=POLL_TIMEOUT + 10,
            offset=offset,
            timeout=POLL_TIMEOUT,
            allowed_updates=["message"],
        )
        if batch is None:
            await asyncio.sleep(3)
            continue
        for update in batch:
            offset = update["update_id"] + 1
            await handle(update, ask)


def main() -> None:
    if not TOKEN:
        sys.exit("Falta TELEGRAM_BOT_TOKEN en .env")
    if not ALLOWED:
        print(
            "Telegram: falta TELEGRAM_ALLOWED_USER_ID; responderé con el id de quien escriba.",
            file=sys.stderr,
        )
    asyncio.run(serve())


if __name__ == "__main__":
    main()
