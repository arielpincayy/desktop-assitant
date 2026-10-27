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
