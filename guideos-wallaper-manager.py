#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# GuideOS.de Wallpaper-Manager
# -----------------------------------------------------------------------------
# Autor: evilware666 & Helga
# Version: 2.1
# Datum: 2025-12-13
# -----------------------------------------------------------------------------

import gi
import os
import threading
import hashlib
import subprocess
from PIL import Image
import webbrowser

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib

WALLPAPER_DIR = os.path.expanduser("~/Bilder/GuideoWallpapers")
THUMB_CACHE_DIR = os.path.expanduser("~/.cache/guideos-wallpaper-manager-thumbs")
FIRST_START_FLAG = os.path.join(THUMB_CACHE_DIR, ".first_start_done")

SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".webp")

os.makedirs(WALLPAPER_DIR, exist_ok=True)
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)


def thumb_name_from_file(file_path):
    h = hashlib.sha256(file_path.encode("utf-8")).hexdigest()
    return os.path.join(THUMB_CACHE_DIR, f"{h}.png")


class WallpaperManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="GuideOS.de Wallpaper-Manager")
        self.set_default_size(1200, 700)
        self.connect("destroy", Gtk.main_quit)

        self.selected_file = None

        self.build_ui()
        self.show_first_start_info()
        self.load_wallpapers_async()
        GLib.timeout_add_seconds(600, self.load_wallpapers_async)

    def show_first_start_info(self):
        if os.path.exists(FIRST_START_FLAG):
            return

        dialog = Gtk.MessageDialog(
            parent=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="Erster Start – Thumbnails werden erstellt"
        )

        dialog.format_secondary_text(
            "⚠️ Achtung! ⚠️\n\n"
            "Beim ersten Start werden alle Wallpaper-Vorschaubilder in einen lokalen Cache geladen.\n\n"
            "Je nach Anzahl der verfügbaren Bilder kann dies einige Minuten dauern – bitte Geduld!\n\n"
            f"Die Thumbnails werden gespeichert unter:\n{THUMB_CACHE_DIR}\n\n"
            "Bei zukünftigen Starts werden nur neue Bilder geladen."
        )

        dialog.run()
        dialog.destroy()

        try:
            with open(FIRST_START_FLAG, "w") as f:
                f.write("ok")
        except:
            pass

    def build_ui(self):
        hb = Gtk.HeaderBar(title="GuideOS.de Wallpaper-Manager")
        hb.set_show_close_button(True)
        self.set_titlebar(hb)

        self.set_btn = Gtk.Button.new_with_label("Als Hintergrund setzen")
        self.set_btn.set_sensitive(False)
        self.set_btn.connect("clicked", self.set_wallpaper)
        hb.pack_end(self.set_btn)

        self.download_btn = Gtk.Button.new_with_label("Download")
        self.download_btn.set_sensitive(False)
        self.download_btn.connect("clicked", self.download_wallpaper)
        hb.pack_end(self.download_btn)

        reload_btn = Gtk.Button.new_with_label("                   Bilder neu laden")
        reload_btn.connect("clicked", self.load_wallpapers_async)
        hb.pack_start(reload_btn)

        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(main_box)

        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.pack_start(left_box, False, False, 0)

        self.status_label = Gtk.Label(label="")
        self.status_label.set_halign(Gtk.Align.START)
        left_box.pack_start(self.status_label, False, False, 0)

        self.cache_btn = Gtk.Button.new_with_label("Cache-Ordner öffnen")
        self.cache_btn.connect("clicked", self.open_cache)
        left_box.pack_start(self.cache_btn, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_width(300)
        left_box.pack_start(scroll, True, True, 0)

        self.flow = Gtk.FlowBox()
        self.flow.set_max_children_per_line(5)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.flow)

        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.pack_end(right_box, True, True, 0)

        preview_scroll = Gtk.ScrolledWindow()
        right_box.pack_end(preview_scroll, True, True, 0)

        self.preview = Gtk.Image()
        preview_scroll.add(self.preview)

    def open_cache(self, button):
        webbrowser.open(f"file://{THUMB_CACHE_DIR}")

    def load_wallpapers_async(self, *args):
        self.flow.foreach(lambda w: self.flow.remove(w))
        self.status_label.set_text("Bilder werden in den Cache geladen …")
        threading.Thread(target=self.load_local_wallpapers, daemon=True).start()

    # -------------------------------------------------------------
    # Lade alle vorhandenen Bilder aus WALLPAPER_DIR
    # -------------------------------------------------------------
    def load_local_wallpapers(self):
        urls = []
        for root, dirs, files in os.walk(WALLPAPER_DIR):
            for file in files:
                if file.lower().endswith(SUPPORTED_FORMATS):
                    urls.append(os.path.join(root, file))

        total = len(urls)
        cached = 0

        # Bereits vorhandene Thumbnails anzeigen
        for url in urls:
            thumb_path = thumb_name_from_file(url)
            if os.path.exists(thumb_path):
                cached += 1
                GLib.idle_add(self.add_thumb_to_grid, url, thumb_path)

        GLib.idle_add(
            lambda: self.status_label.set_text(
                f"Cache: {cached}/{total} geladen – {total - cached} werden erstellt"
            )
        )

        # Fehlende Thumbnails erstellen
        created = 0
        for url in urls:
            thumb_path = thumb_name_from_file(url)
            if not os.path.exists(thumb_path):
                try:
                    im = Image.open(url)
                    im.thumbnail((150, 150))
                    im.save(thumb_path, "PNG")
                    created += 1

                    GLib.idle_add(self.add_thumb_to_grid, url, thumb_path)
                    GLib.idle_add(
                        lambda c=cached, cr=created, t=total: self.status_label.set_text(
                            f"Cache: {c + cr}/{t} geladen – {t - (c + cr)} verbleibend"
                        )
                    )
                except:
                    continue

        GLib.idle_add(
            lambda: self.status_label.set_text(
                f"Cache aktuell – {total} Bilder verfügbar"
            )
        )

    def add_thumb_to_grid(self, url, thumb_path):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(thumb_path)
        except:
            return False

        event = Gtk.EventBox()
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.NONE)
        frame.set_margin_top(5)
        frame.set_margin_bottom(5)
        frame.set_margin_left(5)
        frame.set_margin_right(5)

        img_widget = Gtk.Image.new_from_pixbuf(pixbuf)
        frame.add(img_widget)
        event.add(frame)

        event.connect("button-press-event", self.thumb_clicked, url)
        self.flow.add(event)
        self.flow.show_all()
        return False

    def thumb_clicked(self, widget, event, url):
        self.selected_file = url
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(url, 1600, 900, True)
        self.preview.set_from_pixbuf(pixbuf)
        self.set_btn.set_sensitive(True)
        self.download_btn.set_sensitive(True)

    def set_wallpaper(self, button):
        if not self.selected_file:
            return
        uri = "file://" + self.selected_file
        subprocess.run(
            [
                "gsettings", "set",
                "org.cinnamon.desktop.background",
                "picture-uri", uri
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    def download_wallpaper(self, button):
        if not self.selected_file:
            return

        dialog = Gtk.FileChooserDialog(
            title="Speichern unter",
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            "Abbrechen", Gtk.ResponseType.CANCEL,
            "Speichern", Gtk.ResponseType.OK
        )
        dialog.set_current_name(os.path.basename(self.selected_file))

        if dialog.run() == Gtk.ResponseType.OK:
            save_path = dialog.get_filename()
            try:
                with open(self.selected_file, "rb") as src, open(save_path, "wb") as dst:
                    dst.write(src.read())
            except Exception as e:
                print("Fehler beim Speichern:", e)

        dialog.destroy()


if __name__ == "__main__":
    win = WallpaperManager()
    win.show_all()
    Gtk.main()
