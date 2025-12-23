# GuideOS.de Wallpaper-Manager
# =============================================================================
# Beschreibung:
# Grafischer Wallpaper-Manager für GuideOS und Cinnamon-basierte Systeme.
# Das Tool lädt Hintergrundbilder aus einem öffentlichen Nextcloud-Ordner,
# erzeugt automatisch Vorschaubilder (Thumbnails) im Cache-Verzeichnis,
# speichert KEINE Vollbilder lokal (außer auf expliziten User-Wunsch)
# und ermöglicht das Setzen oder Herunterladen von Wallpapers
# über eine einsteigerfreundliche GTK-Oberfläche.
#
# Verhalten:
# - Hinweis erscheint das das Programm beim benutzen eine Internetverbindung hergestellt
# - Abbruch-Button zum Programm verlassen
# - Thumbnails werden direkt vom Nextcloud-Share erzeugt und in:
#     ~/.cache/guideos-wallpaper-manager-thumbs
#   gespeichert.
# - Thumbnails verbleiben dauerhaft im Cache.
# - Beim Start:
#     * Nextcloud-Ordner wird nach Dateien durchsucht.
#     * Für jede Datei:
#         - Wenn Thumbnail bereits im Cache → wird nur aus dem Cache geladen.
#         - Wenn Thumbnail fehlt → wird einmalig aus Nextcloud geladen.
# - Vollbilder werden NICHT automatisch heruntergeladen.
# - Vollbilder werden NUR geladen, wenn der User:
#     - "Als Hintergrund setzen" oder
#     - "Download"
#   anklickt.
#
# Funktionen:
# - Laden von Wallpapers aus einem öffentlichen Nextcloud-Ordner (nur Meta + Thumbs)
# - Persistenter Thumbnail-Cache
# - Nur neue Bilder werden nachgeladen
# - Asynchrones Laden (GUI bleibt bedienbar)
# - Vorschau in hoher Auflösung (vom Nextcloud-Preview, nicht Vollbild)
# - Setzen des Wallpapers unter Cinnamon (lädt dann das Vollbild)
# - Optionaler Download einzelner Bilder (lädt dann das Vollbild)
# - Zoom-Funktion in der Vorschau mit Mausrad
#
# Abhängigkeiten:
# - python3-gi, gir1.2-gtk-3.0
# - python3-requests
#
# Autor(en): evilware666 & Helga
# Projekt:   GuideOS
# Version:   2.2
# Datum:     21.12.2025
# Lizenz:    Frei nutzbar im Rahmen von GuideOS
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

# Lokaler Ordner für Vollbilder, falls der User explizit
# "Download" oder "Als Hintergrund setzen" nutzt.
WALLPAPER_DIR = os.path.expanduser("~/Bilder/GuideOS-Wallpapers")

# Cache-Verzeichnis für Thumbnails
THUMB_CACHE_DIR = os.path.expanduser("~/.cache/guideos-wallpaper-manager-thumbs")
FIRST_START_FLAG = os.path.join(THUMB_CACHE_DIR, ".first_start_done")

SUPPORTED_FORMATS = (".jpg", ".jpeg", ".png", ".webp")

# Nextcloud-Share-Konfiguration
NEXTCLOUD_URL = "https://cloud.guideos.de/public.php/webdav/"
NEXTCLOUD_TOKEN = "Z663zsACWL2XiSP"

os.makedirs(WALLPAPER_DIR, exist_ok=True)
os.makedirs(THUMB_CACHE_DIR, exist_ok=True)


def thumb_name_from_file(identifier: str) -> str:
    """
    Erzeugt einen eindeutigen Thumbnail-Dateinamen im Cache.
    'identifier' ist hier der DEkodierte Dateiname im Nextcloud-Share.
    """
    h = hashlib.sha256(identifier.encode("utf-8")).hexdigest()
    return os.path.join(THUMB_CACHE_DIR, f"{h}.png")


def list_online_wallpapers():
    """
    Holt die Dateiliste aus dem öffentlichen Nextcloud-Share.
    Gibt eine Liste von DEkodierten Dateinamen zurück, die Bildformate sind.
    """
    try:
        response = requests.request(
            "PROPFIND",
            NEXTCLOUD_URL,
            auth=(NEXTCLOUD_TOKEN, "")
        )

        if response.status_code not in (207, 200):
            print("Fehler beim Abrufen der Nextcloud-Liste:", response.status_code)
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

            if file_url.endswith("/"):
                # Ordner ignorieren
                continue

            # Basename holen und DEkodieren (Umlaute, Leerzeichen, etc.)
            filename = os.path.basename(file_url)
            filename = unquote(filename)

            if filename.lower().endswith(SUPPORTED_FORMATS):
                files.append(filename)

        return files

    except Exception as e:
        print("Fehler beim Abrufen der Dateiliste:", e)
        return []


def get_preview_url(filename: str, width: int, height: int) -> str:
    """
    Baut die URL für die Nextcloud-Preview (Thumbnail oder große Vorschau).

    WICHTIG:
    - Preview-API erwartet den Dateinamen UNENCODED.
    - Nur 'file=/Name mit Leerzeichen.png' – kein quote() verwenden!
    """
    return (
        "https://cloud.guideos.de/index.php/apps/files_sharing/publicpreview/"
        f"{NEXTCLOUD_TOKEN}?file=/{filename}&x={width}&y={height}&a=1"
    )


def get_full_file_url(filename: str) -> str:
    """
    URL des Vollbildes über WebDAV.

    HIER ist quote() korrekt, weil WebDAV encodierte Pfade akzeptiert.
    """
    return NEXTCLOUD_URL + quote(filename)


def download_thumbnail(filename: str) -> str | None:
    """
    Lädt ein 150x150 Thumbnail direkt von Nextcloud,
    ohne das Original herunterzuladen.
    Speichert es im THUMB_CACHE_DIR.
    Lädt NICHT neu, wenn bereits im Cache vorhanden.
    """
    thumb_path = thumb_name_from_file(filename)

    # Bereits im Cache → nicht erneut laden
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
            return thumb_path
        else:
            print(f"Fehler beim Laden des Thumbnails ({filename}):", r.status_code)
    except Exception as e:
        print("Fehler beim Laden des Thumbnails:", e)

    return None


def download_full_image_to_path(filename: str, target_path: str) -> bool:
    """
    Lädt das Vollbild von Nextcloud an einen angegebenen Pfad.
    Wird NUR genutzt, wenn der User explizit Download oder
    "Als Hintergrund setzen" wählt.
    """
    url = get_full_file_url(filename)
    try:
        r = requests.get(url, stream=True, auth=(NEXTCLOUD_TOKEN, ""), timeout=60)
        if r.status_code == 200:
            with open(target_path, "wb") as f:
                for chunk in r.iter_content(8192):
                    if chunk:
                        f.write(chunk)
            return True
        else:
            print(f"Fehler beim Laden des Vollbildes ({filename}):", r.status_code)
    except Exception as e:
        print("Fehler beim Laden des Vollbildes:", e)
    return False


class ZoomableImage(Gtk.Box):
    """Ein benutzerdefiniertes Widget, das ein Bild mit Zoom-Funktion anzeigt."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        
        # Zoom-Faktor (1.0 = 100%)
        self.zoom_factor = 1.0
        self.min_zoom = 0.1
        self.max_zoom = 10.0
        self.zoom_step = 0.2
        
        # Erstelle einen ScrolledWindow für das Image
        self.scrolled_window = Gtk.ScrolledWindow()
        self.scrolled_window.set_policy(
            Gtk.PolicyType.AUTOMATIC, 
            Gtk.PolicyType.AUTOMATIC
        )
        self.pack_start(self.scrolled_window, True, True, 0)
        
        # Erstelle das Image-Widget
        self.image = Gtk.Image()
        self.image.set_halign(Gtk.Align.CENTER)
        self.image.set_valign(Gtk.Align.CENTER)
        
        # EventBox für Maus-Events
        self.event_box = Gtk.EventBox()
        self.event_box.add(self.image)
        self.scrolled_window.add(self.event_box)
        
        # Event-Maske für Mausrad-Ereignisse
        self.event_box.set_events(Gdk.EventMask.SCROLL_MASK | 
                                 Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.event_box.connect("scroll-event", self.on_scroll)
        
        # Aktueller Pixbuf
        self.current_pixbuf = None
        
        # Ursprüngliche Pixbuf-Dimensionen
        self.original_width = 0
        self.original_height = 0
        
    def set_from_pixbuf(self, pixbuf):
        """Setzt das Bild und zeigt es skaliert an, um in das Fenster zu passen."""
        if pixbuf is None:
            return
            
        self.current_pixbuf = pixbuf
        self.original_width = pixbuf.get_width()
        self.original_height = pixbuf.get_height()
        
        # Berechne die verfügbare Größe
        allocation = self.scrolled_window.get_allocation()
        available_width = allocation.width
        available_height = allocation.height
        
        # Wenn keine Größe verfügbar ist, verwende Standardwerte
        if available_width <= 0 or available_height <= 0:
            available_width = 800
            available_height = 600
        
        # Berechne Skalierungsfaktor, um das Bild in das Fenster zu passen
        width_ratio = available_width / self.original_width
        height_ratio = available_height / self.original_height
        self.zoom_factor = min(width_ratio, height_ratio, 1.0)
        
        # Begrenze den minimalen Zoom
        if self.zoom_factor < self.min_zoom:
            self.zoom_factor = self.min_zoom
            
        self.update_image()
        
    def update_image(self):
        """Aktualisiert das angezeigte Bild basierend auf dem aktuellen Zoom-Faktor."""
        if self.current_pixbuf is None:
            return
            
        # Berechne neue Dimensionen
        new_width = int(self.original_width * self.zoom_factor)
        new_height = int(self.original_height * self.zoom_factor)
        
        # Skaliere das Bild
        scaled_pixbuf = self.current_pixbuf.scale_simple(
            new_width, 
            new_height, 
            GdkPixbuf.InterpType.BILINEAR
        )
        
        # Setze das skalierte Bild
        self.image.set_from_pixbuf(scaled_pixbuf)
        
        # Stelle sicher, dass das Image-Widget die richtige Größe hat
        self.image.set_size_request(new_width, new_height)
        
    def on_scroll(self, widget, event):
        """Behandelt Mausrad-Ereignisse zum Zoomen."""
        # Prüfe ob Strg-Taste gedrückt ist
        state = event.get_state()
        ctrl_pressed = state & Gdk.ModifierType.CONTROL_MASK
        
        if ctrl_pressed:
            # Bestimme Scroll-Richtung
            if event.direction == Gdk.ScrollDirection.UP:
                # Vergrößern
                self.zoom_factor += self.zoom_step
            elif event.direction == Gdk.ScrollDirection.DOWN:
                # Verkleinern
                self.zoom_factor -= self.zoom_step
            elif hasattr(event, 'delta_y') and event.delta_y != 0:
                # Für glattes Scrollen (Touchpad)
                if event.delta_y < 0:
                    self.zoom_factor += self.zoom_step
                else:
                    self.zoom_factor -= self.zoom_step
                
            # Begrenze den Zoom-Faktor
            self.zoom_factor = max(self.min_zoom, min(self.max_zoom, self.zoom_factor))
            
            # Aktualisiere das Bild
            self.update_image()
            
            # Verhindere weiteres Scrollen
            return True
            
        return False
        
    def reset_zoom(self):
        """Setzt den Zoom so, dass das Bild komplett im Fenster sichtbar ist."""
        if self.current_pixbuf is None:
            return
            
        # Berechne die verfügbare Größe
        allocation = self.scrolled_window.get_allocation()
        available_width = allocation.width
        available_height = allocation.height
        
        if available_width <= 0 or available_height <= 0:
            available_width = 800
            available_height = 600
        
        # Berechne Skalierungsfaktor, um das Bild in das Fenster zu passen
        width_ratio = available_width / self.original_width
        height_ratio = available_height / self.original_height
        self.zoom_factor = min(width_ratio, height_ratio, 1.0)
        
        # Begrenze den minimalen Zoom
        if self.zoom_factor < self.min_zoom:
            self.zoom_factor = self.min_zoom
            
        self.update_image()


class WallpaperManager(Gtk.Window):
    def __init__(self):
        super().__init__(title="GuideOS Wallpaper-Manager")
        self.set_default_size(1200, 700)
        self.connect("destroy", Gtk.main_quit)

        # Statt lokalem Pfad merken wir uns den Dateinamen im Share
        self.selected_filename = None

        # Zeige den Erststart-Dialog VOR dem Aufbau der UI
        if not self.show_first_start_info():
            # Wenn der Benutzer abgebrochen hat, beende das Programm
            sys.exit(0)
        
        self.build_ui()
        self.load_wallpapers_async()
        # Alle 10 Minuten neu einlesen (z. B. neue Bilder im Share)
        GLib.timeout_add_seconds(600, self.load_wallpapers_async)

    def show_first_start_info(self):
        """
        Zeigt den Erststart-Dialog.
        Gibt True zurück, wenn der Dialog mit OK bestätigt wurde,
        False wenn abgebrochen wurde.
        """
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
            "                                           ⚠️ Achtung! ⚠️\n\n"
            "Beim ersten Start werden alle Wallpaper-Vorschaubilder "
            "aus dem Online-Ordner in einen lokalen Cache geladen.\n\n"
            "Es werden nur kleine Thumbnails gespeichert – keine Vollbilder.\n\n"
            f"Die Thumbnails werden gespeichert unter:\n{THUMB_CACHE_DIR}\n\n"
            "Bei zukünftigen Starts werden nur neue Bilder geladen; "
            "bereits vorhandene Thumbnails bleiben im Cache."
        )

        # Setze den Fokus auf OK (Standardverhalten)
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
            # Abbrechen wurde gewählt
            return False

    def build_ui(self):
        hb = Gtk.HeaderBar(title="Strg + Mausrad zum Zoomen")
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
        
        # Zoom-Reset Button
        #self.reset_zoom_btn = Gtk.Button.new_with_label("Zoom zurücksetzen")
        #self.reset_zoom_btn.set_sensitive(False)
        #self.reset_zoom_btn.connect("clicked", self.reset_zoom)
        #hb.pack_end(self.reset_zoom_btn)

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
        
        # Info-Label für Zoom-Funktion - Jetzt zentriert über das gesamte Widget
        zoom_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        zoom_box.set_halign(Gtk.Align.CENTER)
        zoom_box.set_valign(Gtk.Align.START)
        zoom_box.set_margin_top(5)
        zoom_box.set_margin_bottom(5)
        
        # Hintergrund für bessere Lesbarkeit
        event_box = Gtk.EventBox()
        zoom_label = Gtk.Label(label="<b></b>")
        zoom_label.set_use_markup(True)
        
        # Optional: Styling für den Hinweis
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(b"""
            .zoom-hint {
                background-color: rgba(0, 0, 0, 0.7);
                color: white;
                padding: 5px 10px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        
        zoom_style_context = event_box.get_style_context()
        zoom_style_context.add_provider(css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        zoom_style_context.add_class("zoom-hint")
        
        event_box.add(zoom_label)
        zoom_box.pack_start(event_box, False, False, 0)
        right_box.pack_start(zoom_box, False, False, 0)

        # Verwende unser ZoomableImage-Widget
        self.preview = ZoomableImage()
        right_box.pack_end(self.preview, True, True, 0)

    def open_cache(self, button):
        webbrowser.open(f"file://{THUMB_CACHE_DIR}")
        
    def reset_zoom(self, button):
        """Setzt den Zoom des Vorschaubildes zurück."""
        self.preview.reset_zoom()

    def load_wallpapers_async(self, *args):
        self.status_label.set_text("Bilder werden in den Cache geladen …")
        threading.Thread(target=self.load_online_wallpapers, daemon=True).start()

    def load_online_wallpapers(self):
        """
        Lädt die Dateiliste vom Nextcloud-Share.
        Verwendat vorhandene Thumbnails aus dem Cache
        und lädt NUR neue Thumbnails herunter.
        Die GUI (FlowBox) wird dabei immer aus dem Cache aufgebaut.
        """
        files = list_online_wallpapers()
        total = len(files)
        loaded = 0

        # FlowBox leeren (GUI), Cache bleibt unverändert
        GLib.idle_add(lambda: self.flow.foreach(lambda w: self.flow.remove(w)))

        for filename in files:
            thumb_path = thumb_name_from_file(filename)

            # 1. Thumbnail existiert bereits im Cache → nur anzeigen
            if os.path.exists(thumb_path):
                loaded += 1
                GLib.idle_add(self.add_thumb_to_grid, filename, thumb_path)
            else:
                # 2. Thumbnail fehlt → einmalig herunterladen
                new_thumb = download_thumbnail(filename)
                if new_thumb:
                    loaded += 1
                    GLib.idle_add(self.add_thumb_to_grid, filename, new_thumb)

            # Status aktualisieren
            GLib.idle_add(
                lambda l=loaded, t=total: self.status_label.set_text(
                    f"Cache: {l}/{t} Thumbnails geladen"
                )
            )

        # Abschlussstatus
        GLib.idle_add(
            lambda: self.status_label.set_text(
                f"         Cache aktuell – {total} Bilder verfügbar"
            )
        )

    def add_thumb_to_grid(self, filename, thumb_path):
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(thumb_path)
        except Exception:
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

        # filename ist unser Identifier für dieses Bild im Share
        event.connect("button-press-event", self.thumb_clicked, filename)
        self.flow.add(event)
        self.flow.show_all()
        return False

    def thumb_clicked(self, widget, event, filename):
        """
        Beim Klick auf ein Thumbnail:
        - Dateinamen merken
        - Große Vorschau (nicht Vollbild) laden
        """
        self.selected_filename = filename

        # Große Vorschau vom Nextcloud-Preview (z. B. 1600x900)
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
                    # Verwende die neue Methode zum Setzen des Pixbufs
                    self.preview.set_from_pixbuf(pixbuf)
                    self.reset_zoom_btn.set_sensitive(True)
                    
                    # Bild wird jetzt automatisch skaliert, um ins Fenster zu passen
                    GLib.idle_add(self.preview.update_image)
            else:
                print(f"Fehler beim Laden der großen Vorschau ({filename}):", r.status_code)
        except Exception as e:
            print("Fehler beim Laden der großen Vorschau:", e)

        self.set_btn.set_sensitive(True)
        self.download_btn.set_sensitive(True)

    def set_wallpaper(self, button):
        """
        Lädt das Vollbild NUR für das ausgewählte Bild herunter
        (falls noch nicht vorhanden) und setzt es als Hintergrund.
        """
        if not self.selected_filename:
            return

        local_full_path = os.path.join(WALLPAPER_DIR, self.selected_filename)

        if not os.path.exists(local_full_path):
            os.makedirs(WALLPAPER_DIR, exist_ok=True)
            ok = download_full_image_to_path(self.selected_filename, local_full_path)
            if not ok:
                print("Konnte Vollbild nicht herunterladen, Abbruch.")
                return

        uri = "file://" + local_full_path
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
        """
        Lädt das Vollbild des ausgewählten Bildes an einen frei
        wählbaren Pfad (User-Dialog).
        """
        if not self.selected_filename:
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
        dialog.set_current_name(self.selected_filename)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            save_path = dialog.get_filename()
            ok = download_full_image_to_path(self.selected_filename, save_path)
            if not ok:
                print("Fehler beim Speichern des Vollbildes.")

        dialog.destroy()


if __name__ == "__main__":
    win = WallpaperManager()
    win.show_all()
    Gtk.main()
