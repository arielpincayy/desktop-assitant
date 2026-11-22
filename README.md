# Mascota virtual para COSMIC

Prototipo en Python GTK3 + WebKitGTK 4.1. El personaje y su animación siguen en
HTML/CSS/JavaScript; `gtk-layer-shell` crea una superficie Wayland anclada,
transparente y sin barra de título.

## Ejecutar

```sh
./mostrar-mascota
```

Para pasar un mensaje propio, usa `--mensaje`:

```sh
./mostrar-mascota --mensaje "¡Hola, Ariel! Ya es hora de una pausa ☕"
```

Cada ejecución muestra el fantasmita azul, que salta y dice el mensaje. Se queda
visible hasta pulsar el botón ×. El resto de la superficie deja pasar los clics.
Sin argumento, muestra «¡Hola caracola! 👋».

## Ventana de recordatorios

Ventana normal GTK + WebKit (`recordatorios.py`, UI en `assets/recordatorios/`) para
listar, crear, editar, completar y borrar recordatorios. Requiere la API en marcha
(`REMINDERS_API_URL`, por defecto `http://localhost:8001`).

```sh
./mostrar-recordatorios.sh
```

## Reiniciar tras cambios

`./reiniciar-ulu.sh` detiene la API/agente y el bot, reinicia Postgres y SearXNG
sin borrar el volumen, y vuelve a levantar todo. Cierra y reabre la ventana de
recordatorios para cargar cambios de UI.

## Cronjobs

Cada recordatorio `pending` se instala en el `crontab` del usuario (líneas con el
marcador `# ulu-reminder`), que ejecuta `recordar.py <id>` y muestra la mascota con
título y descripción. La API resincroniza el crontab al crear, editar o borrar, y al
arrancar. Requiere Postgres arriba al disparar.

Si la PC estaba apagada a la hora de un recordatorio, al iniciar sesión se muestran
los perdidos de uno en uno (`recordar.py --pendientes`; el autostart lo crea
`./instalar-ulu.sh`). Un recurrente perdido varias veces se anuncia una sola vez.

Los recordatorios de «una vez» pasan a `announced` al anunciarse: salen del crontab y
de la lista principal (sección «Anunciados») y se borran de la DB 5 días después, al
crear el siguiente recordatorio.

## Acciones de los recordatorios

Cada recordatorio tiene un campo `action`:

- `NULL` (sin acción): la mascota muestra el título y la descripción.
- `agent`: al dispararse, ULU usa el título y la descripción como instrucción, ejecuta
  la acción con sus herramientas y muestra la respuesta.
- `command`: el comando guardado en la tabla `comandos` se ejecuta con `/bin/sh` al
  dispararse; la mascota muestra su salida (stdout y stderr). Tiene un timeout de 30 s.

Puedes elegir la acción en la ventana de recordatorios o pedírselo a ULU por chat.
Los comandos se ejecutan con los permisos del usuario y sin confirmación; se usa el
entorno de cron, así que emplea rutas absolutas si el comando no está en `PATH`.
La API escucha solo en `localhost`: no la expongas fuera de la máquina. El agente solo
crea recordatorios con `action='command'` cuando el usuario lo pide explícitamente.

La columna `action` se añade a las bases existentes al arrancar la API
(`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`), así que reinicia `main.py` tras actualizar.

## Agente de ejemplo

El directorio `agent/` contiene un agente pequeño con Google ADK y LiteLLM. Lee
`AGENT_API_KEY` desde `.env` y responde una pregunta fija declarada en
`agent/main.py`.

1. Copia `.env.example` a `.env` y coloca tu API key de TokenHarbor en
   `AGENT_API_KEY`.
2. Instala dependencias dentro del entorno virtual del proyecto:

   ```sh
   .venv/bin/python -m pip install google-adk litellm python-dotenv
   ```

3. Ejecuta el agente:

   ```sh
   .venv/bin/python -m agent.main
   ```

Puedes cambiar el modelo LiteLLM con `AGENT_MODEL` en `.env` y el endpoint con
`AGENT_API_BASE`. El agente agrega `openai/` al nombre corto del modelo para
usar la API compatible con OpenAI de TokenHarbor. La pregunta fija se cambia
editando `QUESTION` en `agent/main.py`.

## API de recordatorios

PostgreSQL corre en Docker (`db`, volumen `pg_data`, red interna
`172.31.255.240/28`, solo en `127.0.0.1:5434`);
la API corre en el venv del proyecto. Define `POSTGRES_PASSWORD` en `.env`
(ver `.env.example`). La API crea las tablas `reminders` y `comandos` con
SQLAlchemy (`metadata.create_all`) al iniciar y escucha en `http://localhost:8001`.

```sh
docker compose up -d
.venv/bin/python main.py   # API + agente ULU (carga .env)
curl http://localhost:8001/health
```

`main.py` también expone `POST /chat` (`{"message": "..."}` → `{"reply": "..."}`):
es el chat con ULU que abre el botón «Hablar con ULU» del formulario de la ventana
de recordatorios. ULU usa libremente las tools de `agent/tools.py`.

### OpenCode desde ULU

La tool `ask_opencode` delega una tarea al CLI de OpenCode (`opencode run`) y
devuelve su respuesta final. Sin `session_id` empieza una sesión nueva; con el
`session_id` devuelto continúa la misma conversación. Trabaja sobre este repo o el
`directory` indicado y usa `--auto`, así que puede editar archivos y ejecutar
comandos sin confirmación. El modelo es el configurado en OpenCode; se puede forzar
por llamada con `model` (`provider/model`). Timeout: 300 s.

Requiere el CLI `opencode` en el `PATH` o `OPENCODE_BIN` con la ruta al ejecutable
(útil al abrir ULU desde el lanzador de escritorio).

### Codex desde ULU

La tool `ask_codex` delega una tarea al CLI de Codex (`codex exec`) y devuelve su
respuesta final. Sin `session_id` empieza una sesión nueva; con el `session_id`
devuelto (el `thread_id` de Codex) continúa la misma conversación
(`codex exec resume`). Trabaja sobre este repo o el `directory` indicado y usa
`--dangerously-bypass-approvals-and-sandbox`, así que puede editar archivos y
ejecutar comandos sin confirmación. El modelo es el configurado en Codex; se puede
forzar por llamada con `model`. Timeout: 300 s.

Requiere el CLI `codex` en el `PATH` o `CODEX_BIN` con la ruta al ejecutable
(útil al abrir ULU desde el lanzador de escritorio).

### Claude desde ULU

La tool `ask_claude` delega una tarea al CLI de Claude Code (`claude -p`) y
devuelve su respuesta final. Sin `session_id` empieza una sesión nueva; con el
`session_id` devuelto continúa la misma conversación (`--resume`). Trabaja sobre
este repo o el `directory` indicado y usa `--dangerously-skip-permissions`, así que
puede editar archivos y ejecutar comandos sin confirmación. El modelo es el
configurado en Claude Code; se puede forzar por llamada con `model`. Timeout: 300 s.

Requiere el CLI `claude` en el `PATH` o `CLAUDE_BIN` con la ruta al ejecutable
(útil al abrir ULU desde el lanzador de escritorio).

Python puede consultar o administrar recordatorios por HTTP:

```python
import requests

response = requests.get(
    "http://localhost:8001/reminders",
    params={"user_id": "usuario", "status": "pending"},
)
print(response.json())
```

La API ofrece `GET /reminders`, `GET /reminders/{id}`, `POST /reminders`,
`PATCH /reminders/{id}` y `DELETE /reminders/{id}`. La documentación interactiva
está en `http://localhost:8001/docs`. Para borrar la base y el volumen:

```sh
docker compose down -v
```

## Telegram

Chat con ULU desde el móvil sin abrir puertos: el bot usa long polling. También
reenvía a tu chat los recordatorios que anuncia la mascota.

1. Habla con @BotFather en Telegram, crea un bot con `/newbot` y copia el token.
2. Define en `.env` `TELEGRAM_BOT_TOKEN` y `TELEGRAM_ALLOWED_USER_ID`, y protege
   el archivo con `chmod 600 .env` (contiene el token). Para obtener tu id, deja
   el id vacío, arranca el bot y mándale cualquier mensaje: responderá con tu id.
   Luego ponlo y reinicia el bot.
3. Arráncalo (si ejecutaste `./instalar-ulu.sh`, arranca solo al iniciar sesión):

   ```sh
   ./ulu-telegram.sh
   ```

   El log está en `~/.local/state/ulu/telegram.log`.

El bot ignora los mensajes de cualquier otro usuario. Tras cada arranque queda
bloqueado: envía `/clave <contraseña>` para usarlo; el mensaje se borra del chat.
La sesión sigue abierta hasta `/salir` o hasta reiniciar el bot. La clave vive en
Postgres (tabla `ulu`, scrypt con sal) y por defecto es `ulu`: cámbiala desde la
ventana de recordatorios con el botón 🔑 *Clave de Telegram*. Usa una clave única:
viaja por Telegram y puede verse en una notificación antes de que el bot la borre.

Al arrancar, `./ulu-telegram.sh` asegura Postgres y `main.py` con `./ulu-api.sh`,
así que las tools funcionan sin abrir la ventana. Un error 409 en el log significa
que hay otra instancia o un webhook.

Con el bot configurado, los recordatorios se envían también a tu chat; pulsa
`/start` al menos una vez para que Telegram permita escribirte. No lo compartas:
tiene las mismas herramientas que ULU, incluidas `ask_opencode` (`--auto`),
`ask_codex` (sin sandbox), `ask_claude` (sin confirmaciones) y los recordatorios
con `action=command`, que ejecutan código en tu PC con tus permisos.

## Requisitos

- Pop!_OS con COSMIC y sesión Wayland.
- Sesión gráfica activa.
- Python 3, PyGObject, GTK 3, WebKitGTK 4.1 y GTK Layer Shell.

En Ubuntu/Pop!_OS 24.04 instala los bindings con:

```sh
sudo apt install gir1.2-gtklayershell-0.1 gir1.2-webkit2-4.1 python3-gi-cairo
```

Al iniciar, la app comprueba que la sesión sea Wayland y que el compositor
anuncie `wlr-layer-shell`; si no, termina con un mensaje en la terminal en vez
de abrir una ventana normal decorada.

## Archivos

- `src/mascota.py`: ventana transparente, topmost, no enfocada y pasante a clics.
- `assets/mascota.html`: globo y ciclo de animación.
- `assets/fantasmita.svg`: personaje vectorial azul.
- `mostrar-mascota`: comando de lanzamiento.
