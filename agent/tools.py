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
DELEGATE_TIMEOUT = 300
DELEGATE_MAX_OUTPUT = 8000
MAX_LIST_ENTRIES = 200
MAX_READ_CHARS = 100_000
ROOT = Path(__file__).resolve().parent.parent
_STATE: dict[tuple[str, str], dict[str, str]] = {}


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


def _path(value: str) -> Path:
    path = Path(value).expanduser()
    return path if path.is_absolute() else ROOT / path


def list_dir(directory: str = ".") -> Any:
    """Lista archivos y carpetas de un directorio de la computadora.

    directory: ruta absoluta (p. ej. "/home/ariel") o relativa al proyecto; "." lista la raíz del proyecto.
    Devuelve el nombre, el tipo ("dir" o "file") y el tamaño en bytes; máximo 200 entradas.
    """
    path = _path(directory)
    if not path.is_dir():
        return {"error": f"No es un directorio: {path}"}
    try:
        entries = sorted(
            path.iterdir(), key=lambda item: (not item.is_dir(), item.name.lower())
        )
    except OSError as exc:
        return {"error": f"No se pudo listar {path}: {exc}"}
    result = []
    for entry in entries[:MAX_LIST_ENTRIES]:
        try:
            size: int | None = entry.stat().st_size
        except OSError:
            size = None
        result.append(
            {"name": entry.name, "type": "dir" if entry.is_dir() else "file", "size": size}
        )
    if len(entries) > MAX_LIST_ENTRIES:
        result.append(
            {"name": f"…{len(entries) - MAX_LIST_ENTRIES} entradas más", "type": "info", "size": None}
        )
    return result


def read_file(path: str) -> Any:
    """Abre un archivo de texto de la computadora y devuelve su contenido.

    path: ruta absoluta o relativa al proyecto.
    Máximo 100 000 caracteres; si el archivo es mayor, lo indica al final.
    """
    target = _path(path)
    if not target.is_file():
        return {"error": f"No existe el archivo: {target}"}
    try:
        content = target.read_text(encoding="utf-8", errors="strict")[: MAX_READ_CHARS + 1]
    except UnicodeDecodeError:
        return {"error": f"{target} no parece un archivo de texto."}
    except OSError as exc:
        return {"error": f"No se pudo leer {target}: {exc}"}
    truncated = len(content) > MAX_READ_CHARS
    return {
        "path": str(target),
        "content": content[:MAX_READ_CHARS] + ("\n… (truncado)" if truncated else ""),
        "truncated": truncated,
    }


def edit_file(path: str, old: str, new: str, replace_all: bool = False) -> Any:
    """Reemplaza un fragmento de texto exacto dentro de un archivo de la computadora.

    path: ruta absoluta o relativa al proyecto.
    old: texto exacto a buscar, con su indentación; debe existir tal cual.
    new: texto que lo reemplaza; usa "" para borrar el fragmento.
    replace_all: True cambia todas las apariciones; False solo la primera.
    Solo edita archivos que el usuario puede escribir sin sudo; no crea archivos.
    """
    target = _path(path)
    if not target.is_file():
        return {"error": f"No existe el archivo: {target}"}
    if not old:
        return {"error": "Indica en `old` el texto exacto a reemplazar."}
    if not os.access(target, os.W_OK):
        return {"error": f"{target} requiere permisos de administrador (sudo); no se editó."}
    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"error": f"{target} no parece un archivo de texto."}
    except OSError as exc:
        return {"error": f"No se pudo leer {target}: {exc}"}
    count = content.count(old)
    if not count:
        return {"error": f"No se encontró ese texto en {target}."}
    try:
        target.write_text(
            content.replace(old, new, -1 if replace_all else 1), encoding="utf-8"
        )
    except OSError as exc:
        return {"error": f"No se pudo escribir {target}: {exc}"}
    return {
        "success": True,
        "path": str(target),
        "replacements": count if replace_all else 1,
    }


def create_file(path: str, content: str = "") -> Any:
    """Crea un archivo nuevo de cualquier extensión con el contenido indicado.

    path: ruta absoluta o relativa al proyecto; la carpeta contenedora debe existir.
    No sobrescribe: devuelve un error si el archivo ya existe (para cambiarlo, usa edit_file).
    """
    target = _path(path)
    if target.exists() or target.is_symlink():
        return {"error": f"Ya existe {target}; no se sobrescribe."}
    if not target.parent.is_dir():
        return {"error": f"No existe la carpeta: {target.parent}"}
    if not os.access(target.parent, os.W_OK):
        return {
            "error": f"{target.parent} requiere permisos de administrador (sudo); no se creó."
        }
    try:
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"error": f"No se pudo crear {target}: {exc}"}
    return {"success": True, "path": str(target), "bytes": len(content.encode())}


def copy_path(source: str, destination: str) -> Any:
    """Copia un archivo o una carpeta a otra ubicación de la computadora.

    source, destination: ruta absoluta o relativa al proyecto.
    Si `destination` es una carpeta existente, copia dentro de ella con el mismo nombre.
    No sobrescribe: devuelve un error si el destino final ya existe.
    """
    src = _path(source)
    if not src.exists():
        return {"error": f"No existe: {src}"}
    dst = _path(destination)
    target = dst / src.name if dst.is_dir() else dst
    if target.exists():
        return {"error": f"Ya existe {target}; no se sobrescribe."}
    if not os.access(src, os.R_OK):
        return {"error": f"No hay permiso de lectura en {src}."}
    if not target.parent.is_dir():
        return {"error": f"No existe la carpeta destino: {target.parent}"}
    if not os.access(target.parent, os.W_OK):
        return {
            "error": f"{target.parent} requiere permisos de administrador (sudo); no se copió."
        }
    try:
        if src.is_dir():
            shutil.copytree(src, target)
        else:
            shutil.copy2(src, target)
    except (OSError, shutil.Error) as exc:
        return {"error": f"No se pudo copiar {src} a {target}: {exc}"}
    return {"success": True, "path": str(target)}


def move_path(source: str, destination: str) -> Any:
    """Mueve o renombra un archivo o una carpeta.

    source, destination: ruta absoluta o relativa al proyecto.
    Si `destination` es una carpeta existente, mueve dentro de ella con el mismo nombre.
    No sobrescribe: devuelve un error si el destino final ya existe.
    """
    src = _path(source)
    if not src.exists():
        return {"error": f"No existe: {src}"}
    dst = _path(destination)
    target = dst / src.name if dst.is_dir() else dst
    if target.exists():
        return {"error": f"Ya existe {target}; no se sobrescribe."}
    if not target.parent.is_dir():
        return {"error": f"No existe la carpeta destino: {target.parent}"}
    for directory in (src.parent, target.parent):
        if not os.access(directory, os.W_OK):
            return {
                "error": f"{directory} requiere permisos de administrador (sudo); no se movió."
            }
    try:
        shutil.move(str(src), str(target))
    except (OSError, shutil.Error) as exc:
        return {"error": f"No se pudo mover {src} a {target}: {exc}"}
    return {"success": True, "path": str(target)}


def delete_path(path: str, confirm: bool = False) -> Any:
    """Borra un archivo o una carpeta con todo su contenido.

    confirm: debe ser True; sin confirmación no borra nada.
    Solo úsala cuando el usuario lo pida claramente.
    """
    if confirm is not True:
        return {"error": "Pasa confirm=True para borrar."}
    target = _path(path)
    if not target.exists() and not target.is_symlink():
        return {"error": f"No existe: {target}"}
    resolved = target.resolve()
    if resolved == ROOT or resolved in ROOT.parents:
        return {"error": f"No borro el proyecto ni una carpeta que lo contiene: {target}"}
    if not os.access(target.parent, os.W_OK):
        return {
            "error": f"{target.parent} requiere permisos de administrador (sudo); no se borró."
        }
    try:
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    except OSError as exc:
        return {"error": f"No se pudo borrar {target}: {exc}"}
    return {"success": True, "path": str(target)}


def compress_path(source: str, destination: str) -> Any:
    """Comprime un archivo o una carpeta en un .zip o un .tar.gz.

    source, destination: ruta absoluta o relativa al proyecto.
    El formato lo decide la extensión del destino: ".zip" o ".tar.gz".
    No sobrescribe: devuelve un error si el destino ya existe.
    """
    src = _path(source)
    if not src.exists():
        return {"error": f"No existe: {src}"}
    dst = _path(destination)
    if dst.exists():
        return {"error": f"Ya existe {dst}; no se sobrescribe."}
    name = dst.name.lower()
    if name.endswith(".zip"):
        fmt, base = "zip", dst.name[:-4]
    elif name.endswith(".tar.gz"):
        fmt, base = "gztar", dst.name[:-7]
    else:
        return {"error": "Usa una extensión .zip o .tar.gz en el destino."}
    if not dst.parent.is_dir():
        return {"error": f"No existe la carpeta destino: {dst.parent}"}
    if not os.access(dst.parent, os.W_OK):
        return {
            "error": f"{dst.parent} requiere permisos de administrador (sudo); no se comprimió."
        }
    try:
        shutil.make_archive(
            str(dst.parent / base), fmt, root_dir=str(src.parent), base_dir=src.name
        )
    except (OSError, shutil.Error) as exc:
        return {"error": f"No se pudo comprimir {src}: {exc}"}
    return {"success": True, "path": str(dst)}


def _opencode_bin() -> str | None:
    fallback = Path.home() / ".opencode/bin/opencode"
    return (
        os.getenv("OPENCODE_BIN")
        or shutil.which("opencode")
        or (str(fallback) if fallback.is_file() else None)
    )


def _state_key(provider: str, directory: str | None) -> tuple[str, str]:
    return provider, str(Path(directory).expanduser().resolve() if directory else ROOT)


def _state(provider: str, directory: str | None) -> dict[str, str]:
    return _STATE.setdefault(_state_key(provider, directory), {})


def _remember(
    provider: str, directory: str | None, session_id: str | None, model: str | None
) -> None:
    state = _state(provider, directory)
    if session_id:
        state["session_id"] = session_id
    if model:
        state["model"] = model


def reset_agent_session(provider: str, directory: str | None = None) -> Any:
    """Empieza una conversación nueva con OpenCode, Codex o Claude.

    provider: "opencode", "codex" o "claude". Conserva el modelo elegido.
    """
    provider = provider.strip().lower()
    if provider not in ("opencode", "codex", "claude"):
        return {"error": "Proveedor inválido; usa opencode, codex o claude."}
    state = _state(provider, directory)
    state.pop("session_id", None)
    return {"success": True, "provider": provider, "model": state.get("model")}


def _run_listing(cmd: list[str], directory: str | None = None) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            cmd,
            cwd=Path(directory).expanduser() if directory else ROOT,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    if result.returncode:
        return None, result.stderr.strip() or f"código {result.returncode}"
    return result.stdout, None


def _claude_sessions(directory: Path, limit: int) -> list[dict[str, Any]]:
    sessions = []
    base = Path.home() / ".claude" / "projects"
    for path in base.glob("*/[0-9a-f-]*.jsonl"):
        try:
            text = path.read_text(errors="replace")
        except OSError:
            continue
        if f'"cwd":"{directory}"' not in text and f'"cwd": "{directory}"' not in text:
            continue
        session_id = path.stem
        title = None
        for line in text.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if event.get("type") == "ai-title":
                title = event.get("aiTitle") or title
            session_id = event.get("sessionId") or session_id
        sessions.append(
            {"id": session_id, "title": title or "Sesión de Claude", "updated": path.stat().st_mtime}
        )
    return sorted(sessions, key=lambda item: item["updated"], reverse=True)[:limit]


def list_sessions(
    provider: str, directory: str | None = None, limit: int = 10
) -> Any:
    """Lista sesiones disponibles para elegir una y continuarla."""
    provider = provider.strip().lower()
    limit = max(1, min(limit, 50))
    cwd = Path(directory).expanduser().resolve() if directory else ROOT
    if provider == "opencode":
        output, error = _run_listing(
            [_opencode_bin() or "opencode", "session", "list", "--format", "json", "-n", str(limit)],
            str(cwd),
        )
        if error:
            return {"error": f"No se pudieron listar sesiones de OpenCode: {error}"}
        try:
            data = json.loads(output or "[]")
            return [
                {"id": item["id"], "title": item.get("title", ""), "updated": item.get("updated")}
                for item in data
            ]
        except (ValueError, TypeError, KeyError):
            return {"error": "OpenCode devolvió una lista de sesiones no válida."}
    if provider == "codex":
        path = Path.home() / ".codex" / "session_index.jsonl"
        sessions = []
        try:
            for line in path.read_text(errors="replace").splitlines():
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                sessions.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("thread_name") or "Sesión de Codex",
                        "updated": item.get("updated_at"),
                    }
                )
        except OSError as exc:
            return {"error": f"No se pudieron listar sesiones de Codex: {exc}"}
        sessions = [item for item in sessions if item["id"]]
        return sorted(sessions, key=lambda item: item["updated"] or "", reverse=True)[:limit]
    if provider == "claude":
        return _claude_sessions(cwd, limit)
    return {"error": "Proveedor inválido; usa opencode, codex o claude."}


def list_models(provider: str, query: str | None = None) -> Any:
    """Lista modelos disponibles; `query` filtra por id o nombre."""
    provider = provider.strip().lower()
    if provider == "opencode":
        output, error = _run_listing([_opencode_bin() or "opencode", "models"])
        models = output.splitlines() if output else []
    elif provider == "codex":
        output, error = _run_listing([_codex_bin() or "codex", "debug", "models"])
        try:
            models = [
                f"{item.get('slug')} — {item.get('display_name', item.get('slug'))}"
                for item in json.loads(output or "{}").get("models", [])
                if item.get("visibility") == "list"
            ]
        except (ValueError, AttributeError):
            models = []
    elif provider == "claude":
        models = ["sonnet", "opus", "haiku", "fable"]
        error = None
    else:
        return {"error": "Proveedor inválido; usa opencode, codex o claude."}
    if error:
        return {"error": f"No se pudieron listar modelos de {provider}: {error}"}
    if query:
        needle = query.lower()
        models = [model for model in models if needle in model.lower()]
    return models[:50]


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
    state = _state("opencode", directory)
    session_id = session_id or state.get("session_id")
    model = model or state.get("model")
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
            timeout=DELEGATE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"OpenCode superó el límite de {DELEGATE_TIMEOUT} s."}
    except OSError as exc:
        return {"error": f"No se pudo ejecutar OpenCode: {exc}"}

    response, new_session, error = _parse_opencode(result.stdout)
    if response:
        if len(response) > DELEGATE_MAX_OUTPUT:
            response = response[:DELEGATE_MAX_OUTPUT] + "\n…"
        _remember("opencode", directory, new_session or session_id, model)
        return {"response": response, "session_id": new_session or session_id}
    detail = error or result.stderr.strip()
    return {
        "error": (detail or f"OpenCode no devolvió texto (código {result.returncode}).")[
            :DELEGATE_MAX_OUTPUT
        ]
    }


def _codex_bin() -> str | None:
    fallbacks = (
        Path.home() / ".local/bin/codex",
        Path.home() / ".codex/packages/standalone/current/bin/codex",
    )
    return (
        os.getenv("CODEX_BIN")
        or shutil.which("codex")
        or next((str(path) for path in fallbacks if path.is_file()), None)
    )


def _parse_codex(stdout: str) -> tuple[str, str | None, str | None]:
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
        kind = event.get("type")
        if kind == "thread.started":
            session_id = event.get("thread_id") or session_id
        elif kind == "item.completed":
            item = event.get("item") or {}
            if item.get("type") == "agent_message":
                text = item.get("text")
                if text:
                    texts.append(text)
            elif item.get("type") == "error":
                error = item.get("message") or error
        elif kind == "error":
            error = event.get("message") or error
        elif kind == "turn.failed":
            error = (event.get("error") or {}).get("message") or error
    return (texts[-1] if texts else ""), session_id, error


def ask_codex(
    prompt: str,
    directory: str | None = None,
    session_id: str | None = None,
    model: str | None = None,
) -> Any:
    """Delega una tarea al CLI de Codex (`codex exec`) y devuelve su respuesta final.

    prompt: tarea completa y autónoma; Codex no puede preguntar durante la ejecución.
    directory: proyecto donde trabajar; por defecto, este repo.
    session_id: id devuelto por una llamada anterior (`thread_id`) para continuar esa conversación.
    model: modelo opcional; sin valor Codex usa su modelo configurado.
    Ejecuta sin sandbox ni confirmaciones: puede editar archivos y lanzar comandos.
    """
    state = _state("codex", directory)
    session_id = session_id or state.get("session_id")
    model = model or state.get("model")
    if not prompt.strip():
        return {"error": "El prompt para Codex está vacío."}
    binary = _codex_bin()
    if binary is None:
        return {"error": "No se encontró el CLI de Codex; instálalo o define CODEX_BIN."}
    cwd = Path(directory).expanduser() if directory else ROOT
    if not cwd.is_dir():
        return {"error": f"El directorio no existe: {cwd}"}
    cmd = [binary, "exec"]
    if session_id:
        cmd.append("resume")
    cmd += [
        "--json",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
    ]
    if model:
        cmd += ["--model", model]
    if session_id:
        cmd.append(session_id)
    cmd.append("-")
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            input=prompt,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=DELEGATE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Codex superó el límite de {DELEGATE_TIMEOUT} s."}
    except OSError as exc:
        return {"error": f"No se pudo ejecutar Codex: {exc}"}

    response, new_session, error = _parse_codex(result.stdout)
    if response:
        if len(response) > DELEGATE_MAX_OUTPUT:
            response = response[:DELEGATE_MAX_OUTPUT] + "\n…"
        _remember("codex", directory, new_session or session_id, model)
        return {"response": response, "session_id": new_session or session_id}
    detail = error or result.stderr.strip()
    return {
        "error": (detail or f"Codex no devolvió texto (código {result.returncode}).")[
            :DELEGATE_MAX_OUTPUT
        ]
    }


def _claude_bin() -> str | None:
    fallbacks = (
        Path.home() / ".local/bin/claude",
        Path.home() / ".claude/local/claude",
    )
    return (
        os.getenv("CLAUDE_BIN")
        or shutil.which("claude")
        or next((str(path) for path in fallbacks if path.is_file()), None)
    )


def _parse_claude(stdout: str) -> tuple[str, str | None, str | None]:
    try:
        data = json.loads(stdout)
    except ValueError:
        return "", None, None
    if not isinstance(data, dict):
        return "", None, None
    text = data.get("result") if isinstance(data.get("result"), str) else ""
    session_id = data.get("session_id")
    if not isinstance(session_id, str):
        session_id = None
    error = None
    if data.get("is_error"):
        error = text or str(
            data.get("error") or data.get("subtype") or "Claude devolvió un error."
        )
    return text, session_id, error


def ask_claude(
    prompt: str,
    directory: str | None = None,
    session_id: str | None = None,
    model: str | None = None,
) -> Any:
    """Delega una tarea al CLI de Claude Code (`claude -p`) y devuelve su respuesta final.

    prompt: tarea completa y autónoma; Claude no puede preguntar durante la ejecución.
    directory: proyecto donde trabajar; por defecto, este repo.
    session_id: id devuelto por una llamada anterior para continuar esa conversación.
    model: modelo opcional; sin valor Claude usa su modelo configurado.
    Ejecuta sin confirmaciones: puede editar archivos y lanzar comandos.
    """
    state = _state("claude", directory)
    session_id = session_id or state.get("session_id")
    model = model or state.get("model")
    if not prompt.strip():
        return {"error": "El prompt para Claude está vacío."}
    binary = _claude_bin()
    if binary is None:
        return {"error": "No se encontró el CLI de Claude; instálalo o define CLAUDE_BIN."}
    cwd = Path(directory).expanduser() if directory else ROOT
    if not cwd.is_dir():
        return {"error": f"El directorio no existe: {cwd}"}
    cmd = [binary, "-p", "--output-format", "json", "--dangerously-skip-permissions"]
    if model:
        cmd += ["--model", model]
    if session_id:
        cmd += ["--resume", session_id]
    cmd += ["--", prompt]
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            errors="replace",
            timeout=DELEGATE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"Claude superó el límite de {DELEGATE_TIMEOUT} s."}
    except OSError as exc:
        return {"error": f"No se pudo ejecutar Claude: {exc}"}

    response, new_session, error = _parse_claude(result.stdout)
    if error:
        return {"error": error[:DELEGATE_MAX_OUTPUT]}
    if response:
        if len(response) > DELEGATE_MAX_OUTPUT:
            response = response[:DELEGATE_MAX_OUTPUT] + "\n…"
        _remember("claude", directory, new_session or session_id, model)
        return {"response": response, "session_id": new_session or session_id}
    detail = result.stderr.strip()
    return {
        "error": (detail or f"Claude no devolvió texto (código {result.returncode}).")[
            :DELEGATE_MAX_OUTPUT
        ]
    }


REMINDER_TOOLS = [
    list_reminders,
    get_reminder,
    create_reminder,
    update_reminder,
    delete_reminder,
    web_search,
    list_dir,
    read_file,
    edit_file,
    create_file,
    copy_path,
    move_path,
    delete_path,
    compress_path,
    list_sessions,
    list_models,
    reset_agent_session,
    ask_opencode,
    ask_codex,
    ask_claude,
]
