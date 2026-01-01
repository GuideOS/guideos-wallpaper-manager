# GuideOS.de Wallpaper-Manager
# =============================================================================
# Beschreibung:
# Grafischer Wallpaper-Manager für GuideOS.de.
# Das Tool lädt Hintergrundbilder vom GuideOS.de Nextcloud-Ordner,
# erzeugt automatisch Vorschaubilder (Thumbnails) im Cache-Verzeichnis,
# speichert KEINE Vollbilder lokal (außer auf expliziten User-Wunsch)
# und ermöglicht das Setzen oder Herunterladen von Wallpapers
# über eine einsteigerfreundliche GTK-Oberfläche mit Sortierung über Kategorien
#
# WICHTIG: Entfernt automatisch alle @-Zeichen aus Pfaden für maximale Kompatibilität
#
# Autor(en): evilware666 & Helga
# Projekt:   GuideOS
# Version:   2.8
# Datum:     01.01.2026
# =============================================================================

import gi
import os
import sys
import threading
import hashlib
import subprocess
import webbrowser
import requests
from xml.etree import ElementTree as ET
from urllib.parse import quote, unquote

gi.require_version("Gtk", "3.0")
gi.require_version("Gdk", "3.0")
from gi.repository import Gtk, GdkPixbuf, GLib, Gdk

# Konfiguration
WALLPAPER_DIR = os.path.expanduser("~/Bilder/GuideOS-Wallpapers")
THUMB_CACHE_DIR = os.path.expanduser("~/.cache/guideos-wallpaper-manager-thumbs")
FIRST_START_FLAG = os.path.join(THUMB_CACHE_DIR, ".first_start_done")
SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".webp")
NEXTCLOUD_URL = "https://cloud.guideos.de/public.php/webdav/"
NEXTCLOUD_TOKEN = "Z663zsACWL2XiSP"

# Verzeichnisse erstellen
os.makedirs(WALLPAPER_DIR, exist_ok=True)
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)


def clean_path(path: str) -> str:
    """
    ENTFERNT ALLE @-ZEICHEN aus Pfaden.
    Wird überall verwendet für maximale Kompatibilität.
    """
    if '@' in path:
        original = path
        cleaned = path.replace('@', '')
        print(f"[CLEAN] '{original}' -> '{cleaned}'")
        return cleaned
    return path


def thumb_name_from_file(identifier: str) -> str:
    """
    Erzeugt Thumbnail-Cache-Namen aus BEREINIGTEM Pfad.
    """
    cleaned = clean_path(identifier)
    h = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()
    return os.path.join(THUMB_CACHE_DIR, f"{h}.png")


def list_online_wallpapers():
    """
    Holt Dateiliste von Nextcloud und entfernt SOFORT alle @-Zeichen.
    """
    try:
        response = requests.request(
            "PROPFIND",
            NEXTCLOUD_URL,
            auth=(NEXTCLOUD_TOKEN, ""),
            headers={'Depth': 'infinity'}
        )

        if response.status_code not in (207, 200):
            print(f"[ERROR] Nextcloud-Liste: {response.status_code}")
            return []

        tree = ET.fromstring(response.text)
        files = []

        for elem in tree.findall(".//{DAV:}response"):
            href = elem.find("{DAV:}href")
            if href is None:
                continue

            file_url = href.text
            if not file_url:
                continue

            # Relativen Pfad extrahieren
            base_path = "/public.php/webdav"
            if file_url.startswith(base_path):
                relative_path = file_url[len(base_path):]
            else:
                relative_path = file_url

            # Ignoriere Root und Ordner
            if relative_path in ("", "/"):
                continue
            if relative_path.endswith("/"):
                continue

            # URL-Decoding
            relative_path = unquote(relative_path)
            
            # Führenden Slash entfernen
            if relative_path.startswith("/"):
                relative_path = relative_path[1:]

            # Nur unterstützte Bildformate
            if relative_path.lower().endswith(SUPPORTED_FORMATS):
                # WICHTIG: @ SOFORT ENTFERNEN
                cleaned_path = clean_path(relative_path)
                files.append(cleaned_path)

        print(f"[INFO] Gefundene Dateien: {len(files)}")
        return files

    except Exception as e:
        print(f"[ERROR] Dateiliste: {e}")
        return []


def get_preview_url(filename: str, width: int, height: int) -> str:
    """
    Nextcloud-Preview URL mit BEREINIGTEM Pfad.
    """
    cleaned = clean_path(filename)
    
    # Nextcloud erwartet führenden Slash
    if not cleaned.startswith("/"):
        cleaned = "/" + cleaned
    
    return (
        "https://cloud.guideos.de/index.php/apps/files_sharing/publicpreview/"
        f"{NEXTCLOUD_TOKEN}?file={cleaned}&x={width}&y={height}&a=1"
    )


def get_full_file_url(filename: str) -> str:
    """
    WebDAV URL mit BEREINIGTEM Pfad.
    """
    cleaned = clean_path(filename)
    encoded = quote(cleaned)
    return NEXTCLOUD_URL + encoded


def download_thumbnail(filename: str) -> str | None:
    """
    Lädt Thumbnail von Nextcloud.
    Verwendet bereinigten Pfad für alles.
    """
    thumb_path = thumb_name_from_file(filename)

    # Cache-Check
    if os.path.exists(thumb_path):
        return thumb_path

    preview_url = get_preview_url(filename, 150, 150)

    try:
        r = requests.get(preview_url, stream=True, timeout=30)
        if r.status_code == 200:
            with open(thumb_path, "wb") as f:
                for chunk in r.iter_content(4096):
                    if chunk:
                        f.write(chunk)
            print(f"[OK] Thumbnail: {filename}")
            return thumb_path
        else:
            print(f"[ERROR] Thumbnail {filename}: HTTP {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Thumbnail: {e}")

    return None


def download_full_image_to_path(filename: str, target_path: str) -> bool:
    """
    Lädt Vollbild von Nextcloud.
    """
    print(f"[DOWNLOAD] Start: {filename}")
    
    url = get_full_file_url(filename)
    
    try:
        # Zielordner erstellen
        target_dir = os.path.dirname(target_path)
        if target_dir:
            os.makedirs(target_dir, exist_ok=True)
        
        # Download
        r = requests.get(url, stream=True, auth=(NEXTCLOUD_TOKEN, ""), timeout=60)
        if r.status_code == 200:
            with open(target_path, "wb") as f:
                total_size = 0
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            print(f"[OK] Download: {filename} ({total_size} Bytes)")
            return True
        else:
            print(f"[ERROR] Download {filename}: HTTP {r.status_code}")
            
    except Exception as e:
        print(f"[ERROR] Download: {e}")
    
    return False


class ZoomableImage(Gtk.Box):
    """Bild mit Zoom-Funktion (Strg + Mausrad)."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_step = 0.2
        
        # Scrolled Window für Bild
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, 
            Gtk.PolicyType.AUTOMATIC
        )
        self.pack_start(self.scrolled_window, True, True, 0)
        
        # EventBox für das gesamte Vorschau-Bild (enthält Bild und Overlay)
        self.preview_event_box = Gtk.EventBox()
        self.scrolled_window.add(self.preview_event_box)
        
        # Overlay-Container für transparenten Dateinamen
        self.overlay = Gtk.Overlay()
        self.preview_event_box.add(self.overlay)
        
        # Bild-Widget
        self.image = Gtk.Image()
        self.image.set_halign(Gtk.Align.CENTER)
        self.image.set_valign(Gtk.Align.CENTER)
        self.overlay.add(self.image)
        
        # Transparentes Overlay-Label für Dateinamen
        self.filename_overlay_label = Gtk.Label()
        self.filename_overlay_label.set_halign(Gtk.Align.START)
        self.filename_overlay_label.set_valign(Gtk.Align.END)
        self.filename_overlay_label.set_margin_start(10)
        self.filename_overlay_label.set_margin_bottom(10)
        self.filename_overlay_label.set_no_show_all(True)
        
        # Label in Overlay einfügen
        self.overlay.add_overlay(self.filename_overlay_label)
        
        # Mausrad-Events
        self.preview_event_box.set_events(Gdk.EventMask.SCROLL_MASK | 
                                         Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.preview_event_box.connect("scroll-event", self.on_scroll)
        
        self.current_pixbuf = None
        self.original_width = 0
        self.original_height = 0
        
    def set_from_pixbuf(self, pixbuf):
        """Setzt Bild mit automatischer Skalierung."""
        if pixbuf is None:
            return
            
        self.current_pixbuf = pixbuf
        self.original_width = pixbuf.get_width()
        self.original_height = pixbuf.get_height()
        
        # Verfügbare Größe berechnen
        allocation = self.scrolled_window.get_allocation()
        available_width = max(allocation.width, 100)
        available_height = max(allocation.height, 100)
        
        # Skalierungsfaktor berechnen
        width_ratio = available_width / self.original_width
        height_ratio = available_height / self.original_height
        self.zoom_factor = min(width_ratio, height_ratio, 1.0)
        
        # Mindest-Zoom
        if self.zoom_factor < self.min_zoom:
            self.zoom_factor = self.min_zoom
            
        self.update_image()
        
    def update_image(self):
        """Aktualisiert Bild basierend auf Zoom-Faktor."""
        if self.current_pixbuf is None:
            return
            
        # Neue Dimensionen
        new_width = int(self.original_width * self.zoom_factor)
        new_height = int(self.original_height * self.zoom_factor)
        
        # Skalieren
        scaled_pixbuf = self.current_pixbuf.scale_simple(
            new_width, 
            new_height, 
            GdkPixbuf.InterpType.BILINEAR
        )
        
        # Anzeigen
        self.image.set_from_pixbuf(scaled_pixbuf)
        self.image.set_size_request(new_width, new_height)
        
    def on_scroll(self, widget, event):
        """Mausrad-Zoom (Strg gedrückt halten)."""
        state = event.get_state()
        ctrl_pressed = state & Gdk.ModifierType.CONTROL_MASK
        
        if ctrl_pressed:
            # Zoom-Richtung
            if event.direction == Gdk.ScrollDirection.UP:
                self.zoom_factor += self.zoom_step
            elif event.direction == Gdk.ScrollDirection.DOWN:
                self.zoom_factor -= self.zoom_step
            elif hasattr(event, 'delta_y') and event.delta_y != 0:
                if event.delta_y < 0:
                    self.zoom_factor += self.zoom_step
                else:
                    self.zoom_factor -= self.zoom_step
            
            # Zoom begrenzen
            self.zoom_factor = max(self.min_zoom, min(self.max_zoom, self.zoom_factor))
            
            # Bild aktualisieren
            self.update_image()
            return True  # Event verarbeitet
            
        return False
        
    def set_filename_overlay(self, filename: str):
        """Setzt transparenten Dateinamen über dem Bild."""
        if filename:
            display_name = filename.replace('_', ' ').replace('-', ' ')
            self.filename_overlay_label.set_markup(
                f'<span foreground="white" background="rgba(0,0,0,0.5)" size="large">'
                f'<b>{display_name}</b></span>'
            )
            self.filename_overlay_label.show()
        else:
            self.filename_overlay_label.hide()


class WallpaperManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="GuideOS Wallpaper-Manager v2.6")
        self.set_default_size(1200, 700)
        self.connect("destroy", Gtk.main_quit)

        # Ausgewählte Datei (bereinigt, ohne @)
        self.selected_filename = None
        
        # Kategorien-Verwaltung
        self.all_files = []  # Alle Dateien
        self.categories = {}  # Kategorie -> [Dateien]
        self.current_category = "Alle Kategorien"  # Aktive Kategorie

        # Erststart-Dialog
        if not self.show_first_start_info():
            sys.exit(0)
        
        # UI aufbauen
        self.build_ui()
        self.load_wallpapers_async()
        
        # Auto-Refresh alle 10 Minuten
        GLib.timeout_add_seconds(600, self.load_wallpapers_async)

    def show_first_start_info(self):
        """Erststart-Dialog mit Thumbnail-Info."""
        if os.path.exists(FIRST_START_FLAG):
            return True

        dialog = Gtk.MessageDialog(
            parent=None,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Erster Start – Thumbnails werden erstellt"
        )

        dialog.format_secondary_text(
            "                                         ⚠️ Achtung! ⚠️\n\n"
            "Beim ersten Start werden alle Wallpaper-Vorschaubilder "
            "aus dem Online-Ordner in einen lokalen Cache geladen.\n\n"
            "Es werden nur kleine Thumbnails gespeichert – keine Vollbilder.\n\n"
            f"Cache-Verzeichnis:\n{THUMB_CACHE_DIR}\n\n"
            "Hinweis: @-Zeichen in Pfaden werden automatisch entfernt."
        )

        dialog.set_default_response(Gtk.ResponseType.OK)
        
        response = dialog.run()
        dialog.destroy()
        
        if response == Gtk.ResponseType.OK:
            try:
                with open(FIRST_START_FLAG, "w") as f:
                    f.write("ok")
            except Exception:
                pass
            return True
        else:
            return False

    def build_ui(self):
        """Baut die Benutzeroberfläche."""
        # Header Bar
        hb = Gtk.HeaderBar(title="Strg + Mausrad zum Zoomen")
        hb.set_show_close_button(True)
        self.set_titlebar(hb)

        # Buttons rechts
        self.set_btn = Gtk.Button.new_with_label("Als Hintergrund setzen")
        self.set_btn.set_sensitive(False)
        self.set_btn.connect("clicked", self.set_wallpaper)
        hb.pack_end(self.set_btn)

        self.download_btn = Gtk.Button.new_with_label("Download")
        self.download_btn.set_sensitive(False)
        self.download_btn.connect("clicked", self.download_wallpaper)
        hb.pack_end(self.download_btn)

        # =============================================================================
        # TEIL 1: Dropdown-Menü für Kategorien (zentriert zwischen den Buttons)
        # =============================================================================
        category_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        category_label = Gtk.Label(label="❗Strg + Mausrad zum zoomen❗          Kategorie:")
        category_box.pack_start(category_label, False, False, 0)
        
        self.category_combo = Gtk.ComboBoxText()
        self.category_combo.set_size_request(200, -1)
        self.category_combo.connect("changed", self.on_category_changed)
        category_box.pack_start(self.category_combo, False, False, 0)
        
        # Dropdown genau zentriert zwischen den Buttons positionieren
        hb.set_custom_title(category_box)
        
        # Buttons links
        reload_btn = Gtk.Button.new_with_label("                   Bilder neu laden")
        reload_btn.connect("clicked", self.load_wallpapers_async)
        hb.pack_start(reload_btn)

        # Haupt-Layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.add(main_box)

        # Linke Seite (Thumbnails)
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.pack_start(left_box, False, False, 0)

        # Status-Label
        self.status_label = Gtk.Label(label="")
        self.status_label.set_halign(Gtk.Align.START)
        left_box.pack_start(self.status_label, False, False, 0)

        # Cache-Button
        self.cache_btn = Gtk.Button.new_with_label("Cache-Ordner öffnen     ")
        self.cache_btn.connect("clicked", self.open_cache)
        left_box.pack_start(self.cache_btn, False, False, 0)

        # Thumbnail-Scrollbereich
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_width(300)
        left_box.pack_start(scroll, True, True, 0)

        # FlowBox für Thumbnails
        self.flow = Gtk.FlowBox()
        self.flow.set_max_children_per_line(5)   
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.add(self.flow)

        # Rechte Seite (Vorschau)
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        main_box.pack_end(right_box, True, True, 0)
        
        # Vorschau-Bild (jetzt direkt ohne Zoom-Hinweis davor)
        self.preview = ZoomableImage()
        right_box.pack_end(self.preview, True, True, 0)

    # =============================================================================
    # TEIL 2: Kategorien-Erkennung und -Verwaltung
    # =============================================================================
    def extract_categories_from_files(self, files):
        """
        Extrahiert Kategorien aus Dateipfaden.
        Ordnerstruktur: "Natur/sonnenuntergang.jpg" ->Kategorie "Natur"
        """
        categories = {"Alle Kategorien": files.copy()}  # Immer alle Dateien enthalten
        
        for file_path in files:
            # Trenne Pfad in Ordner und Dateiname
            if "/" in file_path:
                # Erster Teil des Pfads ist die Kategorie
                category = file_path.split("/")[0]
                
                if category not in categories:
                    categories[category] = []
                
                categories[category].append(file_path)
            else:
                # Dateien ohne Ordner kommen in "Sonstiges"
                if "Sonstiges" not in categories:
                    categories["Sonstiges"] = []
                categories["Sonstiges"].append(file_path)
        
        return categories

    def update_category_dropdown(self):
        """Aktualisiert das Kategorie-Dropdown-Menü."""
        # Alte Einträge löschen
        self.category_combo.remove_all()
        
        # Kategorien sortieren und hinzufügen
        sorted_categories = sorted(self.categories.keys())
        
        # "Alle Kategorien" immer zuerst
        if "Alle Kategorien" in sorted_categories:
            sorted_categories.remove("Alle Kategorien")
            sorted_categories.insert(0, "Alle Kategorien")
        
        # "Sonstiges" ans Ende
        if "Sonstiges" in sorted_categories:
            sorted_categories.remove("Sonstiges")
            sorted_categories.append("Sonstiges")
        
        for category in sorted_categories:
            count = len(self.categories[category])
            self.category_combo.append_text(f"{category} ({count})")
        
        # Aktive Kategorie auswählen
        for i, category in enumerate(sorted_categories):
            if category == self.current_category:
                self.category_combo.set_active(i)
                break

    def reset_status_label(self):
        """Setzt das Status-Label auf den Standardtext zurück."""
        if self.current_category in self.categories:
            count = len(self.categories[self.current_category])
            self.status_label.set_text(f"     Kategorie: '{self.current_category}': {count} Bilder")

    # =============================================================================
    # TEIL 3: Filter-Funktion für die linke Seitenansicht
    # =============================================================================
    def on_category_changed(self, combo):
        """Wird aufgerufen, wenn eine Kategorie ausgewählt wird."""
        text = combo.get_active_text()
        if not text:
            return
        
        # Extrahiere Kategorienamen aus dem Text (entfernt die Anzahl in Klammern)
        category_name = text.split(" (")[0]
        
        if category_name != self.current_category:
            self.current_category = category_name
            self.filter_thumbnails_by_category()

    def filter_thumbnails_by_category(self):
        """Filtert Thumbnails basierend auf der ausgewählten Kategorie."""
        # GUI leeren
        self.flow.foreach(lambda w: self.flow.remove(w))
        
        if self.current_category in self.categories:
            files_to_show = self.categories[self.current_category]
            
            # Thumbnails für die aktuelle Kategorie laden/anzeigen
            for filename in files_to_show:
                thumb_path = thumb_name_from_file(filename)
                if os.path.exists(thumb_path):
                    self.add_thumb_to_grid(filename, thumb_path)
        
        # Status-Update
        self.reset_status_label()

    def open_cache(self, button):
        """Öffnet Cache-Ordner im Dateimanager."""
        webbrowser.open(f"file://{THUMB_CACHE_DIR}")

    def load_wallpapers_async(self, *args):
        """Startet Thumbnail-Laden im Hintergrund."""
        self.status_label.set_text("Bilder werden geladen …")
        threading.Thread(target=self.load_online_wallpapers, daemon=True).start()

    def load_online_wallpapers(self):
        """Lädt Thumbnails (Hintergrund-Thread)."""
        files = list_online_wallpapers()
        total = len(files)
        loaded = 0

        # Dateien speichern
        self.all_files = files.copy()
        
        # =============================================================================
        # Kategorien aus Dateien extrahieren
        # =============================================================================
        self.categories = self.extract_categories_from_files(files)
        
        # GUI-Updates im Main-Thread
        GLib.idle_add(self.update_category_dropdown)

        # GUI leeren
        GLib.idle_add(lambda: self.flow.foreach(lambda w: self.flow.remove(w)))

        for filename in files:  # filename ist BEREINIGT (ohne @)
            thumb_path = thumb_name_from_file(filename)

            # Aus Cache laden oder neu downloaden
            if os.path.exists(thumb_path):
                loaded += 1
                # Nur in GUI laden, wenn zur aktuellen Kategorie gehörend
                if self.current_category == "Alle Kategorien" or \
                   (self.current_category in self.categories and 
                    filename in self.categories[self.current_category]):
                    GLib.idle_add(self.add_thumb_to_grid, filename, thumb_path)
            else:
                new_thumb = download_thumbnail(filename)
                if new_thumb:
                    loaded += 1
                    # Nur in GUI laden, wenn zur aktuellen Kategorie gehörend
                    if self.current_category == "Alle Kategorien" or \
                       (self.current_category in self.categories and 
                        filename in self.categories[self.current_category]):
                        GLib.idle_add(self.add_thumb_to_grid, filename, new_thumb)

            # Status-Update
            GLib.idle_add(
                lambda l=loaded, t=total: self.status_label.set_text(
                    f"            Cache: {l}/{t} Thumbnails"
                )
            )

        # Finaler Status
        GLib.idle_add(
            lambda: self.status_label.set_text(
                f"Bereit – {total} Bilder verfügbar"
            )
        )
        # Rücksetzen auf Kategorie-Info
        GLib.idle_add(self.reset_status_label)

    def add_thumb_to_grid(self, filename, thumb_path):
        """Fügt Thumbnail zur Grid hinzu."""
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(thumb_path)
        except Exception:
            return False

        # Thumbnail-Container
        event = Gtk.EventBox()
        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.NONE)
        frame.set_margin_top(5)
        frame.set_margin_bottom(5)
        frame.set_margin_start(5)
        frame.set_margin_end(5)

        # Bild
        img_widget = Gtk.Image.new_from_pixbuf(pixbuf)
        frame.add(img_widget)
        event.add(frame)

        # Klick-Event
        event.connect("button-press-event", self.thumb_clicked, filename)
        self.flow.add(event)
        self.flow.show_all()
        return False

    def thumb_clicked(self, widget, event, filename):
        """Wird aufgerufen wenn Thumbnail angeklickt wird."""
        print(f"[CLICK] Ausgewählt: {filename}")
        self.selected_filename = filename

        # Status-Label nur den Dateinamen anzeigen (ohne Kategorie-Info)
        display_name = filename.replace('_', ' ').replace('-', ' ')
        self.status_label.set_text(f"     Ausgewählt: {display_name}")

        # Große Vorschau laden
        preview_url = get_preview_url(filename, 1600, 900)

        try:
            r = requests.get(preview_url, stream=True, timeout=60)
            if r.status_code == 200:
                loader = GdkPixbuf.PixbufLoader()
                for chunk in r.iter_content(8192):
                    if chunk:
                        loader.write(chunk)
                loader.close()
                pixbuf = loader.get_pixbuf()
                if pixbuf:
                    self.preview.set_from_pixbuf(pixbuf)
                    GLib.idle_add(self.preview.update_image)
                    
                    # Transparenten Dateinamen über dem Bild anzeigen
                    self.preview.set_filename_overlay(filename)
            else:
                print(f"[ERROR] Vorschau {filename}: HTTP {r.status_code}")
        except Exception as e:
            print(f"[ERROR] Vorschau: {e}")

        # Buttons aktivieren
        self.set_btn.set_sensitive(True)
        self.download_btn.set_sensitive(True)

    def set_wallpaper(self, button):
        """Setzt Bild als Desktop-Hintergrund."""
        if not self.selected_filename:
            return

        print(f"[SET] Setze Hintergrund: {self.selected_filename}")
        
        # Lokaler Pfad (bereinigt)
        local_full_path = os.path.join(WALLPAPER_DIR, self.selected_filename)

        # Herunterladen falls nötig
        if not os.path.exists(local_full_path):
            print(f"[SET] Download benötigt...")
            os.makedirs(os.path.dirname(local_full_path), exist_ok=True)
            
            if not download_full_image_to_path(self.selected_filename, local_full_path):
                print("[ERROR] Download fehlgeschlagen")
                return

        # Hintergrund setzen
        uri = "file://" + local_full_path
        try:
            subprocess.run(
                [
                    "gsettings", "set",
                    "org.cinnamon.desktop.background",
                    "picture-uri", uri
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print("[OK] Hintergrund gesetzt")
            
            # Erfolgsmeldung
            dialog = Gtk.MessageDialog(
                parent=self,
                flags=0,
                message_type=Gtk.MessageType.INFO,
                buttons=Gtk.ButtonsType.OK,
                text="Hintergrund gesetzt"
            )
            dialog.format_secondary_text("Der Hintergrund wurde erfolgreich gesetzt.")
            dialog.run()
            dialog.destroy()
            
        except subprocess.CalledProcessError as e:
            print(f"[ERROR] gsettings: {e}")

    def download_wallpaper(self, button):
        """Lädt Bild herunter (Speichern unter Dialog)."""
        if not self.selected_filename:
            return

        # Dateiname für Dialog
        basename = os.path.basename(self.selected_filename)
        
        dialog = Gtk.FileChooserDialog(
            title="Speichern unter",
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            "Abbrechen", Gtk.ResponseType.CANCEL,
            "Speichern", Gtk.ResponseType.OK
        )
        dialog.set_current_name(basename)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            save_path = dialog.get_filename()
            print(f"[DOWNLOAD] Speichere nach: {save_path}")
            
            if download_full_image_to_path(self.selected_filename, save_path):
                print("[OK] Download erfolgreich")
            else:
                print("[ERROR] Download fehlgeschlagen")

        dialog.destroy()


if __name__ == "__main__":
    print("=" * 60)
    print("GuideOS Wallpaper-Manager v2.6 (@-AutoClean)")
    print("=" * 60)
    win = WallpaperManager()
    win.show_all()
    Gtk.main()
