#!/usr/bin/env python3
# -----------------------------------------------------------------------------
# GuideOS Wallpaper-Manager
# -----------------------------------------------------------------------------
# Autor: evilware666 & Helga
# Version: 1.2
# Datum: 2025-12-06
# -----------------------------------------------------------------------------
# Beschreibung:
# Ein grafisches Tool zum Anzeigen, Herunterladen und Setzen von Wallpapers
# von der Webseite https://guideos.de/wallpapers/.
# 
# Funktionen:
# - Anzeige von Thumbnails aller verfügbaren Wallpapers
# - Auswählen eines Wallpapers und Vorschau in Originalgröße
# - Als Desktop-Hintergrund setzen (Cinnamon)
# - Download des ausgewählten Wallpapers
# - Auswahl eines eigenen lokalen Wallpaper-Ordners für den Download
# - Anzeige eines Ladehinweises beim Abrufen der Bilder
# -----------------------------------------------------------------------------


import gi
import os
import threading
import requests
import io
import subprocess
from bs4 import BeautifulSoup
from PIL import Image

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib

WALLPAPER_DIR = os.path.expanduser("~/Bilder/GuideoWallpapers")
GUVIDEOS_URL = "https://guideos.de/wallpapers/"
SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".webp")

os.makedirs(WALLPAPER_DIR, exist_ok=True)

class WallpaperManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="GuideOS.de Wallpaper-Manager")
        self.set_default_size(1200, 700)
        self.connect("destroy", Gtk.main_quit)

        self.selected_file = None
        self.thumbs = []

        self.build_ui()
        self.load_wallpapers_async()

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

        reload_btn = Gtk.Button.new_with_label("                    Bilder neu laden")
        reload_btn.connect("clicked", self.load_wallpapers_async)
        hb.pack_start(reload_btn)

        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(main_box)

        # Linke Seite: Status-Label + Thumbnails
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.pack_start(left_box, False, False, 0)

        # Hinweis-Label für Ladeprozess oben
        self.status_label = Gtk.Label(label="")
        self.status_label.set_justify(Gtk.Justification.CENTER)
        self.status_label.set_halign(Gtk.Align.START)  # linksbündig
        left_box.pack_start(self.status_label, False, False, 0)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_width(300)
        left_box.pack_start(scroll, True, True, 0)

        self.flow = Gtk.FlowBox()
        self.flow.set_max_children_per_line(5)
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.flow)

        # Rechte Seite: Vorschau + Spinner
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.pack_end(right_box, True, True, 0)

        preview_scroll = Gtk.ScrolledWindow()
        right_box.pack_end(preview_scroll, True, True, 0)
        self.preview = Gtk.Image()
        self.preview.set_halign(Gtk.Align.CENTER)
        self.preview.set_valign(Gtk.Align.CENTER)
        preview_scroll.add_with_viewport(self.preview)

        self.spinner = Gtk.Spinner()
        right_box.pack_start(self.spinner, False, False, 0)

    # -------------------------------------------------------
    # Lade Wallpapers asynchron
    # -------------------------------------------------------
    def load_wallpapers_async(self, *args):
        self.flow.foreach(lambda w: self.flow.remove(w))
        self.spinner.start()
        self.status_label.set_text("                BILDER WERDEN GELADEN . . .")
        threading.Thread(target=self.scrape_wallpapers, daemon=True).start()

    # -------------------------------------------------------
    # Scrapen von guideos.de
    # -------------------------------------------------------
    def scrape_wallpapers(self):
        try:
            r = requests.get(GUVIDEOS_URL, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            imgs = soup.find_all("img")
            urls = []
            for img in imgs:
                src = img.get("src")
                if src and src.lower().endswith(SUPPORTED_FORMATS):
                    if src.startswith("/"):
                        src = "https://guideos.de" + src
                    urls.append(src)
        except:
            urls = []

        GLib.idle_add(self.populate_grid, urls)

    # -------------------------------------------------------
    # Grid füllen mit Thumbnails
    # -------------------------------------------------------
    def populate_grid(self, urls):
        self.spinner.stop()
        self.status_label.set_text("")  # Hinweis ausblenden
        self.thumbs = []
        for url in urls:
            try:
                r = requests.get(url, timeout=10)
                im = Image.open(io.BytesIO(r.content))
                im.thumbnail((150, 150))
                buf = io.BytesIO()
                im.save(buf, format="PNG")
                buf.seek(0)
                loader = GdkPixbuf.PixbufLoader.new_with_type("png")
                loader.write(buf.getvalue())
                loader.close()
                pixbuf = loader.get_pixbuf()
            except:
                continue

            event = Gtk.EventBox()
            frame = Gtk.Frame()
            frame.set_shadow_type(Gtk.ShadowType.NONE)
            frame.set_margin_bottom(5)
            frame.set_margin_top(5)
            frame.set_margin_left(5)
            frame.set_margin_right(5)
            img_widget = Gtk.Image.new_from_pixbuf(pixbuf)
            frame.add(img_widget)
            event.add(frame)
            event.connect("button-press-event", self.thumb_clicked, url)
            self.flow.add(event)
            self.thumbs.append(event)

        self.flow.show_all()

    # -------------------------------------------------------
    # Klick auf Thumbnail
    # -------------------------------------------------------
    def thumb_clicked(self, widget, event, url):
        local_name = os.path.basename(url)
        local_path = os.path.join(WALLPAPER_DIR, local_name)
        if not os.path.exists(local_path):
            try:
                r = requests.get(url, timeout=10)
                with open(local_path, "wb") as f:
                    f.write(r.content)
            except:
                return
        self.selected_file = local_path
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(local_path, 1600, 900, True)
        self.preview.set_from_pixbuf(pixbuf)
        self.set_btn.set_sensitive(True)
        self.download_btn.set_sensitive(True)

    # -------------------------------------------------------
    # Hintergrund setzen
    # -------------------------------------------------------
    def set_wallpaper(self, button):
        if not getattr(self, "selected_file", None):
            return
        uri = "file://" + self.selected_file
        try:
            subprocess.run(["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", uri])
        except:
            pass

    # -------------------------------------------------------
    # Wallpaper herunterladen
    # -------------------------------------------------------
    def download_wallpaper(self, button):
        if not getattr(self, "selected_file", None):
            return
        dialog = Gtk.FileChooserDialog(
            title="Speichern unter",
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons("Abbrechen", Gtk.ResponseType.CANCEL,
                           "Speichern", Gtk.ResponseType.OK)
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
