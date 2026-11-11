#!/usr/bin/env python3
"""Ventana para administrar recordatorios (GTK3 + WebKitGTK, como la mascota)."""

import os
from pathlib import Path
from urllib.parse import urlencode

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import GLib, Gtk, WebKit2

import CONFIG

HTML = Path(__file__).resolve().parent / "assets" / "recordatorios" / "index.html"
API_URL = os.getenv("REMINDERS_API_URL", "http://localhost:8001").rstrip("/")

# prgname = nombre de ulu.desktop: así el dock/Wayland asocia la ventana al icono
GLib.set_prgname("ulu")
GLib.set_application_name("ULU")
ICON = Path(__file__).resolve().parent / "assets" / "fantasmita.svg"
Gtk.Window.set_default_icon_from_file(str(ICON))

win = Gtk.Window(title="ULU")
win.set_default_size(440, 680)
win.connect("destroy", Gtk.main_quit)

webview = WebKit2.WebView()
# La página es file://: sin esto el fetch a la API se bloquea por CORS.
webview.get_settings().set_allow_universal_access_from_file_urls(True)
webview.load_uri(f"{HTML.as_uri()}?{urlencode({'api': API_URL, 'user': CONFIG.USER_ID})}")
win.add(webview)
win.show_all()
Gtk.main()
