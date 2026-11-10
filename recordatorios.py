#!/usr/bin/env python3
"""Ventana para administrar recordatorios (GTK3 + WebKitGTK, como la mascota)."""

import os
from pathlib import Path
from urllib.parse import urlencode

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("WebKit2", "4.1")
from gi.repository import Gtk, WebKit2

import CONFIG

HTML = Path(__file__).resolve().parent / "assets" / "recordatorios" / "index.html"
API_URL = os.getenv("REMINDERS_API_URL", "http://localhost:8001").rstrip("/")

win = Gtk.Window(title="Recordatorios")
win.set_default_size(440, 680)
win.connect("destroy", Gtk.main_quit)

webview = WebKit2.WebView()
# La página es file://: sin esto el fetch a la API se bloquea por CORS.
webview.get_settings().set_allow_universal_access_from_file_urls(True)
webview.load_uri(f"{HTML.as_uri()}?{urlencode({'api': API_URL, 'user': CONFIG.USER_ID})}")
win.add(webview)
win.show_all()
Gtk.main()
