"""Tools de Google ADK para operar sobre la API de reminders."""

import os
from typing import Any

import requests

import CONFIG

API_URL = os.getenv("REMINDERS_API_URL", "http://localhost:8001").rstrip("/")
TIMEOUT_SECONDS = 5


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

    status: filtro opcional, "pending" (por hacer) o "done" (completado). Sin filtro devuelve todos.
    Úsala también para encontrar el id de un recordatorio cuando el usuario no lo da.
    """
    params: dict[str, str] = {"user_id": CONFIG.USER_ID}
    if status:
        params["status"] = status
    return _request("GET", "/reminders", params=params)


def get_reminder(reminder_id: int) -> Any:
    """Consulta un recordatorio por su id. Devuelve un error si no existe o no es del usuario."""
    reminder = _request("GET", f"/reminders/{reminder_id}")
    if isinstance(reminder, dict) and reminder.get("user_id") != CONFIG.USER_ID:
        return {"error": "Recordatorio no encontrado para el usuario actual."}
    return reminder


def create_reminder(
    title: str,
    remind_at: str,
    description: str | None = None,
    timezone: str = "America/Guayaquil",
) -> Any:
    """Crea un recordatorio para el usuario actual (queda en estado "pending").

    remind_at: fecha/hora ISO 8601 en hora local de `timezone`, p. ej. "2026-11-10T17:00:00".
    timezone: nombre IANA, p. ej. "America/Guayaquil".
    """
    return _request(
        "POST",
        "/reminders",
        json={
            "user_id": CONFIG.USER_ID,
            "title": title,
            "description": description,
            "remind_at": remind_at,
            "timezone": timezone,
        },
    )


def update_reminder(
    reminder_id: int,
    title: str | None = None,
    description: str | None = None,
    remind_at: str | None = None,
    timezone: str | None = None,
    status: str | None = None,
) -> Any:
    """Edita solo los campos indicados de un recordatorio propio.

    remind_at: ISO 8601 en hora local de `timezone`, p. ej. "2026-11-10T17:00:00".
    status: "pending" o "done" (usa "done" para marcarlo como completado).
    """
    current = get_reminder(reminder_id)
    if not isinstance(current, dict) or current.get("user_id") != CONFIG.USER_ID:
        return current
    changes = {
        key: value
        for key, value in {
            "title": title,
            "description": description,
            "remind_at": remind_at,
            "timezone": timezone,
            "status": status,
        }.items()
        if value is not None
    }
    if not changes:
        return {"error": "Indica al menos un campo para actualizar."}
    return _request("PATCH", f"/reminders/{reminder_id}", json=changes)


def delete_reminder(reminder_id: int) -> Any:
    """Elimina un recordatorio propio cuando el usuario lo haya solicitado claramente."""
    current = get_reminder(reminder_id)
    if not isinstance(current, dict) or current.get("user_id") != CONFIG.USER_ID:
        return current
    return _request("DELETE", f"/reminders/{reminder_id}")


REMINDER_TOOLS = [
    list_reminders,
    get_reminder,
    create_reminder,
    update_reminder,
    delete_reminder,
]
