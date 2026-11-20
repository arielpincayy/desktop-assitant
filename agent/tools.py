"""Tools de Google ADK para operar sobre la API de reminders."""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import litellm
import requests

import CONFIG

API_URL = os.getenv("REMINDERS_API_URL", "http://localhost:8001").rstrip("/")
TIMEOUT_SECONDS = 5
OPENCODE_TIMEOUT = 300
OPENCODE_MAX_OUTPUT = 8000
ROOT = Path(__file__).resolve().parent.parent


def _request(method: str, path: str, **kwargs: Any) -> Any:
    try:
        response = requests.request(
            method, f"{API_URL}{path}", timeout=TIMEOUT_SECONDS, **kwargs
        )
        response.raise_for_status()
    except requests.Timeout:
        return {"error": "La API de recordatorios agotó el tiempo de espera."}
    except requests.ConnectionError:
        return {"error": f"No se pudo conectar con la API de recordatorios ({API_URL})."}
    except requests.HTTPError as exc:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        return {"error": f"Error HTTP {response.status_code}: {detail}"}
    except requests.RequestException as exc:
        return {"error": f"Error al consultar la API: {exc}"}

    if response.status_code == 204:
        return {"success": True}
    try:
        return response.json()
    except ValueError:
        return {"error": "La API devolvió una respuesta no válida."}


def list_reminders(status: str | None = None) -> Any:
    """Lista los recordatorios del usuario actual.

    status: filtro opcional, "pending" (por hacer), "announced" (ya anunciado) o "done" (completado). Sin filtro devuelve todos.
    Úsala también para encontrar el id de un recordatorio cuando el usuario no lo da.
    """
    params: dict[str, str] = {"user_id": CONFIG.USER_ID}
    # Sin razonamiento el modelo manda "null"/"none" como texto: solo estos valores filtran.
    if status in ("pending", "announced", "done"):
        params["status"] = status
    return _request("GET", "/reminders", params=params)


def web_search(query: str) -> Any:
    """Busca en la web (SearXNG) y devuelve hasta 5 resultados con título, url y fragmento.

    Úsala solo cuando el usuario pida información externa actual (precios, noticias, clima, datos).
    No lee el contenido completo de las páginas: solo los fragmentos.
    """
    try:
        results = litellm.search(
            query=query, search_provider="searxng", max_results=5
        ).results
    except Exception as exc:
        return {"error": f"Falló la búsqueda web: {exc}"}
    return [
        {"title": r.title, "url": r.url, "snippet": r.snippet} for r in results[:5]
    ]


def get_reminder(reminder_id: int) -> Any:
    """Consulta un recordatorio por su id. Devuelve un error si no existe o no es del usuario."""
    reminder = _request("GET", f"/reminders/{reminder_id}")
    if isinstance(reminder, dict) and reminder.get("user_id") != CONFIG.USER_ID:
        return {"error": "Recordatorio no encontrado para el usuario actual."}
    return reminder


def create_reminder(
    title: str,
    schedule: str,
    description: str | None = None,
    timezone: str = "America/Guayaquil",
    action: str | None = None,
    command: str | None = None,
    instruction: str | None = None,
) -> Any:
    """Crea un recordatorio para el usuario actual (queda en estado "pending").

    schedule: cron de 5 campos "min hora díaMes mes díaSemana" (0=domingo) en hora local de `timezone`.
    Ejemplos: una vez el 10-nov a las 17:00 "0 17 10 11 *"; cada día 09:00 "0 9 * * *";
    lunes a viernes 08:30 "30 8 * * 1-5"; cada 2 horas "0 */2 * * *"; cada 15 min "*/15 * * * *".
    Para recordatorios de una sola vez usa fecha concreta; al dispararse pasa a "announced".
    timezone: nombre IANA, p. ej. "America/Guayaquil".
    action: None para solo avisar; "agent" para que ULU ejecute `instruction` al dispararse;
    "command" para ejecutar `command` con el shell y mostrar su salida.
    command: comando de shell a ejecutar cuando action="command".
    instruction: orden que ejecuta el agente cuando action="agent".
    """
    if isinstance(action, str):
        action = action.strip().lower() or None
    if action in ("none", "null"):
        action = None
    return _request(
        "POST",
        "/reminders",
        json={
            "user_id": CONFIG.USER_ID,
            "title": title,
            "description": description,
            "schedule": schedule,
            "timezone": timezone,
            "action": action,
            "command": command,
            "instruction": instruction,
        },
    )


def update_reminder(
    reminder_id: int,
    title: str | None = None,
    description: str | None = None,
    schedule: str | None = None,
    timezone: str | None = None,
    status: str | None = None,
    action: str | None = None,
    command: str | None = None,
    instruction: str | None = None,
) -> Any:
    """Edita solo los campos indicados de un recordatorio propio.

    schedule: (opcional) cron de 5 campos "min hora díaMes mes díaSemana" (0=domingo) en hora local de `timezone`.
    Ejemplos: una vez el 10-nov a las 17:00 "0 17 10 11 *"; cada día 09:00 "0 9 * * *";
    lunes a viernes 08:30 "30 8 * * 1-5"; cada 2 horas "0 */2 * * *"; cada 15 min "*/15 * * * *".
    Para recordatorios de una sola vez usa fecha concreta; al dispararse pasa a "announced".
    status: "pending" o "done" (usa "done" para marcarlo como completado).
    action: "agent", "command" o "none" para quitar la acción.
    command: nuevo comando de shell cuando action="command".
    instruction: nueva orden del agente cuando action="agent".
    """
    current = get_reminder(reminder_id)
    if not isinstance(current, dict) or current.get("user_id") != CONFIG.USER_ID:
        return current
    changes = {
        key: value
        for key, value in {
            "title": title,
            "description": description,
            "schedule": schedule,
            "timezone": timezone,
            "status": status,
            "command": command,
            "instruction": instruction,
        }.items()
        if value is not None
    }
    if isinstance(action, str):
        action = action.strip().lower() or None
    if action in ("none", "null"):
        changes["action"] = None
    elif action is not None:
        changes["action"] = action
    if not changes:
        return {"error": "Indica al menos un campo para actualizar."}
    return _request("PATCH", f"/reminders/{reminder_id}", json=changes)


def delete_reminder(reminder_id: int) -> Any:
    """Elimina un recordatorio propio cuando el usuario lo haya solicitado claramente."""
    current = get_reminder(reminder_id)
    if not isinstance(current, dict) or current.get("user_id") != CONFIG.USER_ID:
        return current
    return _request("DELETE", f"/reminders/{reminder_id}")


def _opencode_bin() -> str | None:
    fallback = Path.home() / ".opencode/bin/opencode"
    return (
        os.getenv("OPENCODE_BIN")
        or shutil.which("opencode")
        or (str(fallback) if fallback.is_file() else None)
    )


def _parse_opencode(stdout: str) -> tuple[str, str | None, str | None]:
    texts: list[str] = []
    session_id = None
    error = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if not isinstance(event, dict):
            continue
        session_id = event.get("sessionID") or session_id
        if event.get("type") == "text":
            text = (event.get("part") or {}).get("text")
            if text:
                texts.append(text)
        elif event.get("type") == "error":
            error = (event.get("error") or {}).get("message") or error
    return "\n".join(texts).strip(), session_id, error


def ask_opencode(
    prompt: str,
    directory: str | None = None,
    session_id: str | None = None,
    model: str | None = None,
) -> Any:
    """Delega una tarea al CLI de OpenCode (`opencode run`) y devuelve su respuesta final.

    prompt: tarea completa y autónoma; OpenCode no puede preguntar durante la ejecución.
    directory: proyecto donde trabajar; por defecto, este repo.
    session_id: id "ses_..." devuelto por una llamada anterior para continuar esa conversación.
    model: "provider/model" opcional; sin valor OpenCode usa su modelo configurado.
    Ejecuta con --auto (sin confirmar permisos): puede editar archivos y lanzar comandos.
    """
    if not prompt.strip():
        return {"error": "El prompt para OpenCode está vacío."}
    binary = _opencode_bin()
    if binary is None:
        return {"error": "No se encontró el CLI de OpenCode; instálalo o define OPENCODE_BIN."}
    cwd = Path(directory).expanduser() if directory else ROOT
    if not cwd.is_dir():
        return {"error": f"El directorio no existe: {cwd}"}
    cmd = [binary, "run", "--format", "json", "--auto", "--archived"]
    if session_id:
        cmd += ["--session", session_id]
    if model:
        cmd += ["--model", model]
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            input=prompt,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=OPENCODE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"OpenCode superó el límite de {OPENCODE_TIMEOUT} s."}
    except OSError as exc:
        return {"error": f"No se pudo ejecutar OpenCode: {exc}"}

    response, new_session, error = _parse_opencode(result.stdout)
    if response:
        if len(response) > OPENCODE_MAX_OUTPUT:
            response = response[:OPENCODE_MAX_OUTPUT] + "\n…"
        return {"response": response, "session_id": new_session}
    detail = error or result.stderr.strip()
    return {
        "error": (detail or f"OpenCode no devolvió texto (código {result.returncode}).")[
            :OPENCODE_MAX_OUTPUT
        ]
    }


REMINDER_TOOLS = [
    list_reminders,
    get_reminder,
    create_reminder,
    update_reminder,
    delete_reminder,
    web_search,
    ask_opencode,
]
