#!/usr/bin/env python3
"""Mascota HTML en una superficie Wayland Layer Shell para COSMIC."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import urlencode

import gi

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
gi.require_version("WebKit2", "4.1")
try:
    gi.require_foreign("cairo")
except ImportError as exc:
    raise SystemExit(
        "Falta python3-gi-cairo; instálalo con: sudo apt install python3-gi-cairo"
    ) from exc

import cairo
from gi.repository import Gdk, Gtk, GtkLayerShell, WebKit2


ROOT = Path(__file__).resolve().parents[0]
PET_HTML = ROOT / "assets" / "mascota.html"
MIN_WIDTH, MIN_HEIGHT = 300, 220


class Mascota(Gtk.Application):
    def __init__(self, message: str) -> None:
        super().__init__(application_id="local.cosmic.MascotaLayerShell", flags=0)
        self.message = message
        self.window: Gtk.ApplicationWindow | None = None
        self.close_button: Gtk.Button | None = None

    def do_activate(self) -> None:
        if self.window is not None:
            self.window.present()
            return

        if not GtkLayerShell.is_supported():
            print(
                "Este compositor no anuncia wlr-layer-shell; no se abrió una ventana normal.",
                file=sys.stderr,
                flush=True,
            )
            self.quit()
            return

        display = Gdk.Display.get_default()
        if display is None:
            print("No se pudo conectar a la sesión gráfica Wayland.", file=sys.stderr, flush=True)
            self.quit()
            return

        monitor = display.get_primary_monitor()
        if monitor is None and display.get_n_monitors() > 0:
            monitor = display.get_monitor(0)

        if monitor is not None:
            geometry = monitor.get_geometry()
            screen_width, screen_height = geometry.width, geometry.height
        else:
            # En algunas sesiones Wayland GdkDisplay no informa un monitor
            # principal, aunque GdkScreen sí expone las dimensiones visibles.
            screen = display.get_default_screen()
            screen_width, screen_height = screen.get_width(), screen.get_height()

        if screen_width <= 0 or screen_height <= 0:
            print("No se pudo determinar el tamaño de la pantalla.", file=sys.stderr, flush=True)
            self.quit()
            return

        width = max(MIN_WIDTH, round(screen_width * 0.9))
        height = max(MIN_HEIGHT, round(screen_height * 0.75))

        self.window = Gtk.ApplicationWindow(application=self)
        self.window.set_title("Mascota COSMIC")
        self.window.set_decorated(False)
        self.window.set_resizable(False)
        self.window.set_accept_focus(False)
        self.window.set_focus_on_map(False)
        self.window.set_default_size(width, height)

        rgba_visual = display.get_default_screen().get_rgba_visual()
        if rgba_visual is None:
            print("La pantalla no ofrece un visual RGBA para transparencia.", file=sys.stderr, flush=True)
            self.quit()
            return
        self.window.set_visual(rgba_visual)

        # Debe inicializarse antes de realizar/mapear la ventana.
        GtkLayerShell.init_for_window(self.window)
        GtkLayerShell.set_namespace(self.window, "cosmic-virtual-pet")
        GtkLayerShell.set_layer(self.window, GtkLayerShell.Layer.OVERLAY)
        if monitor is not None:
            GtkLayerShell.set_monitor(self.window, monitor)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_anchor(self.window, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.RIGHT, 24)
        GtkLayerShell.set_margin(self.window, GtkLayerShell.Edge.BOTTOM, 24)
        GtkLayerShell.set_exclusive_zone(self.window, 0)
        GtkLayerShell.set_keyboard_mode(self.window, GtkLayerShell.KeyboardMode.NONE)

        transparent = Gdk.RGBA()
        transparent.parse("rgba(0, 0, 0, 0)")

        content_manager = WebKit2.UserContentManager()
        content_manager.register_script_message_handler("petBounds")
        content_manager.connect(
            "script-message-received::petBounds", self.on_pet_bounds
        )
        webview = WebKit2.WebView.new_with_user_content_manager(content_manager)
        webview.set_background_color(transparent)
        webview.set_size_request(width, height)
        webview.set_hexpand(True)
        webview.set_vexpand(True)

        overlay = Gtk.Overlay()
        overlay.add(webview)

        close_button = Gtk.Button(label="×")
        self.close_button = close_button
        close_button.set_tooltip_text("Cerrar mascota")
        close_button.get_style_context().add_class("pet-close")
        close_button.set_halign(Gtk.Align.START)
        close_button.set_valign(Gtk.Align.START)
        close_button.connect("clicked", self.on_close_button)
        overlay.add_overlay(close_button)
        self.window.add(overlay)

        query = urlencode({"mensaje": self.message})
        webview.load_uri(f"{PET_HTML.as_uri()}?{query}")

        css = Gtk.CssProvider()
        css.load_from_data(
            b"window { background-color: rgba(0, 0, 0, 0); border: none; box-shadow: none; }"
            b".pet-close { min-width: 28px; min-height: 28px; padding: 0; "
            b"border: 1px solid rgba(26,45,70,.16); border-radius: 50%; "
            b"background: rgba(255,255,255,.94); color: #34445a; "
            b"font-weight: 600; font-size: 19px; box-shadow: 0 2px 8px rgba(16,24,40,.15); }"
            b".pet-close:hover { background: white; color: #10243c; }"
        )
        Gtk.StyleContext.add_provider_for_screen(
            display.get_default_screen(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        # La ventana solo recibe eventos en el área del botón. El personaje y
        # el globo dejan pasar los clics a las aplicaciones que están debajo.
        self.window.realize()
        input_region = cairo.Region()
        self.window.get_window().input_shape_combine_region(input_region, 0, 0)
        self.window.show_all()
        self.window.present()
        print("Mascota Layer Shell mostrada; ciérrala con el botón ×.", flush=True)

    def on_close_button(self, *_args) -> None:
        self.quit()

    def on_pet_bounds(self, _manager, result) -> None:
        if self.window is None or self.close_button is None:
            return

        try:
            x, y = (
                int(value)
                for value in result.get_js_value().to_string().split(",")
            )
        except (TypeError, ValueError):
            return

        self.close_button.set_margin_start(x)
        self.close_button.set_margin_top(y)
        window_surface = self.window.get_window()
        if window_surface is not None:
            region = cairo.Region(cairo.RectangleInt(x, y, 32, 32))
            window_surface.input_shape_combine_region(region, 0, 0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Muestra la mascota virtual COSMIC.")
    parser.add_argument(
        "-m", "--mensaje", default="¡Hola caracola! 👋",
        help="texto que mostrará el personaje",
    )
    args = parser.parse_args()
    if not Gtk.init_check() or Gdk.Display.get_default() is None:
        print("No se pudo abrir una sesión gráfica; ejecuta esto desde COSMIC Wayland.", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(Mascota(args.mensaje).run(None))
