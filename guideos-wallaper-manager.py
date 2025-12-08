#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
############################################################################################
GuideOS Wallpaper-Manager
--------------------------------
- plattformabhängigem Setzen des Desktops (Cinnamon/GNOME, feh, Windows, macOS)
- Hell/Dunkel-Theme für Dialoge

Autor: evilware666 & Helga
Lizenz: MIT
Datum: 2025-11-08
Version 1.1
"""
###############################################################################################

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from PIL import Image, ImageTk, ImageOps
import os
import threading
import subprocess
import platform
import time
import json
import hashlib
import logging
from logging.handlers import RotatingFileHandler
from concurrent.futures import ThreadPoolExecutor
from functools import partial

# --- Konfiguration / Defaults ---
URL = "https://guideos.de/wallpapers/"
APP_NAME = "GuideOS Wallpaper-Manager"
DEFAULT_CONFIG = {
    "cache_dir": os.path.expanduser("~/.cache/guideos_wallpapers"),
    "max_thumbnail_threads": 8,
    "max_download_threads": 4,
    "download_retries": 2,
    "request_timeout": 12
}
CONFIG_FILE = "config.json"
PLACEHOLDER_SIZE = (220, 130)

# --- Hilfsfunktionen ---
def ensure_dir(p):
    try:
        os.makedirs(p, exist_ok=True)
    except Exception:
        pass

def load_config():
    cfg = DEFAULT_CONFIG.copy()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                user_cfg = json.load(f)
            cfg.update(user_cfg)
        except Exception:
            pass
    ensure_dir(cfg["cache_dir"])
    return cfg

CONFIG = load_config()

# --- Logging ---
LOG_DIR = os.path.expanduser("~/.local/share/guideos_wallpapers_logs")
ensure_dir(LOG_DIR)
log_file = os.path.join(LOG_DIR, "app.log")
logger = logging.getLogger("guideos")
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# --- Netzwerk-Utilities ---
def safe_get(url, stream=False, timeout=None, headers=None, retries=1):
    timeout = timeout or CONFIG["request_timeout"]
    headers = headers or {}
    last_exc = None
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, stream=stream, timeout=timeout, headers=headers)
            r.raise_for_status()
            return r
        except Exception as e:
            logger.warning("Request fehlgeschlagen %s (Versuch %d/%d): %s", url, attempt+1, retries+1, e)
            last_exc = e
            time.sleep(0.5 + attempt * 0.5)
    raise last_exc

def url_to_hash(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()

# --- Cache für Thumbnails (mit Metadata) ---
class ThumbnailCache:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        ensure_dir(self.base_dir)

    def meta_path(self, url_hash):
        return os.path.join(self.base_dir, url_hash + ".json")

    def img_path(self, url_hash):
        return os.path.join(self.base_dir, url_hash + ".img")

    def get(self, url):
        h = url_to_hash(url)
        img_p = self.img_path(h)
        meta_p = self.meta_path(h)
        if os.path.exists(img_p):
            try:
                with open(img_p, "rb") as f:
                    data = f.read()
                meta = {}
                if os.path.exists(meta_p):
                    try:
                        meta = json.load(open(meta_p, "r", encoding="utf-8"))
                    except Exception:
                        meta = {}
                return data, meta
            except Exception as e:
                logger.debug("Cache-Lesen fehlgeschlagen: %s", e)
        return None, None

    def put(self, url, content, response):
        h = url_to_hash(url)
        img_p = self.img_path(h)
        meta_p = self.meta_path(h)
        try:
            with open(img_p, "wb") as f:
                f.write(content)
            meta = {}
            meta["etag"] = response.headers.get("ETag")
            meta["last_modified"] = response.headers.get("Last-Modified")
            meta["url"] = url
            with open(meta_p, "w", encoding="utf-8") as f:
                json.dump(meta, f)
        except Exception as e:
            logger.warning("Cache-Schreiben fehlgeschlagen: %s", e)

    def get_headers_for(self, url):
        hsh = url_to_hash(url)
        meta_p = self.meta_path(hsh)
        if os.path.exists(meta_p):
            try:
                meta = json.load(open(meta_p, "r", encoding="utf-8"))
                headers = {}
                if meta.get("etag"):
                    headers["If-None-Match"] = meta["etag"]
                if meta.get("last_modified"):
                    headers["If-Modified-Since"] = meta["last_modified"]
                return headers
            except Exception:
                pass
        return {}

THUMB_CACHE = ThumbnailCache(CONFIG["cache_dir"])

# --- Placeholder image ---
def make_placeholder(size=PLACEHOLDER_SIZE, text="kein Bild"):
    w, h = size
    img = Image.new("RGBA", (w, h), (100, 100, 100, 255))
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 32))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    try:
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        tw, th = draw.textsize(text, font=font)
        draw.text(((w-tw)//2, (h-th)//2), text, fill=(240, 240, 240), font=font)
    except Exception:
        pass
    return img

PLACEHOLDER_PIL = make_placeholder()

# --- Set wallpaper (verbessert für Cinnamon/GNOME + feh fallback) ---
def set_wallpaper(filepath):
    """
    Setzt das Wallpaper plattformspezifisch.
    Rückgabe: (ok: bool, err_text: str or None)
    Für Cinnamon/GNOME wird gsettings mit file://-URI verwendet.
    Als Fallback wird 'feh' versucht.
    """
    filepath = os.path.abspath(filepath)
    system = platform.system()
    err_parts = []

    try:
        if system == "Windows":
            try:
                import ctypes
                bmp_path = filepath
                if not filepath.lower().endswith('.bmp'):
                    from PIL import Image
                    tmp_bmp = os.path.join(os.path.dirname(filepath), "tmp_wallpaper.bmp")
                    Image.open(filepath).convert("RGB").save(tmp_bmp, "BMP")
                    bmp_path = tmp_bmp
                SPI_SETDESKWALLPAPER = 20
                res = ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, bmp_path, 3)
                if not res:
                    return False, "SystemParametersInfoW returned false"
                return True, None
            except Exception as e:
                return False, str(e)

        elif system == "Darwin":
            try:
                safe_path = filepath.replace('"', '\\"')
                script = (
                    'tell application "System Events"\n'
                    '  set everyDesktops to a reference to every desktop\n'
                    '  repeat with d in everyDesktops\n'
                    f'    set picture of d to "{safe_path}"\n'
                    '  end repeat\n'
                    'end tell'
                )
                res = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
                if res.returncode != 0:
                    err_text = (res.stderr or res.stdout or "").strip()
                    return False, err_text or "osascript returned non-zero"
                return True, None
            except Exception as e:
                return False, str(e)

        else:
            # Linux: bevorzugt gsettings (Cinnamon/GNOME), fallback feh
            uri = f"file://{filepath}"

            # Cinnamon schema
            try:
                res = subprocess.run(
                    ["gsettings", "set", "org.cinnamon.desktop.background", "picture-uri", uri],
                    capture_output=True, text=True
                )
                if res.returncode == 0:
                    logger.info("Wallpaper gesetzt via gsettings (cinnamon): %s", filepath)
                    return True, None
                err_parts.append(("cinnamon", (res.stderr or res.stdout or "gsettings returned non-zero").strip()))
            except FileNotFoundError:
                err_parts.append(("cinnamon", "gsettings nicht gefunden"))
            except Exception as e:
                err_parts.append(("cinnamon", str(e)))

            # GNOME fallback
            try:
                res2 = subprocess.run(
                    ["gsettings", "set", "org.gnome.desktop.background", "picture-uri", uri],
                    capture_output=True, text=True
                )
                if res2.returncode == 0:
                    logger.info("Wallpaper gesetzt via gsettings (gnome): %s", filepath)
                    return True, None
                err_parts.append(("gnome", (res2.stderr or res2.stdout or "gsettings returned non-zero").strip()))
            except FileNotFoundError:
                err_parts.append(("gnome", "gsettings nicht gefunden"))
            except Exception as e:
                err_parts.append(("gnome", str(e)))

            # feh fallback
            try:
                resf = subprocess.run(["feh", "--bg-scale", filepath], capture_output=True, text=True)
                if resf.returncode == 0:
                    logger.info("Wallpaper gesetzt via feh: %s", filepath)
                    return True, None
                err_parts.append(("feh", (resf.stderr or resf.stdout or "feh returned non-zero").strip()))
            except FileNotFoundError:
                err_parts.append(("feh", "feh nicht gefunden"))
            except Exception as e:
                err_parts.append(("feh", str(e)))

            err_text = "\n".join(f"{k}: {v}" for k, v in err_parts)
            logger.warning("set_wallpaper failed: %s", err_text)
            return False, err_text or "Unbekannter Fehler beim Setzen des Hintergrunds"

    except Exception as e:
        logger.exception("set_wallpaper overall failed: %s", e)
        return False, str(e)

# --- Haupt-Applikation ---
class WallpaperApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_NAME)
        self.geometry("1200x800")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # theme detection + setup
        self.dark_mode = self.detect_system_theme()
        self.setup_theme()

        # logging/status
        self.status_var = tk.StringVar(value="Bereit.")
        self._create_widgets()

        # daten
        self.wallpapers = []
        self.categories = []
        self.selected = set()

        # thread executors
        self.thumb_executor = ThreadPoolExecutor(max_workers=CONFIG["max_thumbnail_threads"])
        self.download_executor = ThreadPoolExecutor(max_workers=CONFIG["max_download_threads"])
        self._thumb_futures = {}
        self._download_futures = []
        self._download_cancel = threading.Event()

        # start
        self.show_start_progress()
        threading.Thread(target=self.load_data_and_render, daemon=True).start()

    def _create_widgets(self):
        title_label = tk.Label(self, text=APP_NAME, font=("Arial", 22, "bold"),
                               bg=self.bg_color, fg=self.fg_color, pady=12)
        title_label.pack(side="top", fill="x")

        toolbar = tk.Frame(self, bg=self.bg_color)
        toolbar.pack(side="top", fill="x", padx=8, pady=6)
        toolbar.grid_columnconfigure(0, weight=1)
        toolbar.grid_columnconfigure(1, weight=1)
        toolbar.grid_columnconfigure(2, weight=1)

        mid = tk.Frame(toolbar, bg=self.bg_color)
        mid.grid(row=0, column=1)

        tk.Label(mid, text="Kategorie:", bg=self.bg_color, fg=self.fg_color).pack(side="left", padx=5)
        self.category_var = tk.StringVar()
        self.category_menu = ttk.Combobox(mid, textvariable=self.category_var, state="readonly", width=50)
        self.category_menu.pack(side="left", padx=5)
        self.category_menu.bind("<<ComboboxSelected>>", lambda e: self.show_images())

        tk.Label(mid, text="Suche:", bg=self.bg_color, fg=self.fg_color).pack(side="left", padx=5)
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(mid, textvariable=self.search_var, width=30,
                                     bg=self.entry_bg, fg=self.fg_color, insertbackground=self.fg_color)
        self.search_entry.pack(side="left", padx=5)
        self.search_entry.bind("<Return>", lambda e: self.show_images())

        btn_frame = tk.Frame(toolbar, bg=self.bg_color)
        btn_frame.grid(row=0, column=2, sticky="e")

        self.select_all_btn = tk.Button(btn_frame, text="Alle auswählen", command=self.select_all,
                                        bg=self.button_bg, fg=self.fg_color)
        self.select_all_btn.pack(side="left", padx=(0,6))

        self.unselect_all_btn = tk.Button(btn_frame, text="Auswahl aufheben", command=self.unselect_all,
                                          bg=self.button_bg, fg=self.fg_color)
        self.unselect_all_btn.pack(side="left", padx=(0,6))

        self.download_btn = tk.Button(btn_frame, text="Auswahl speichern", command=self.save_selected,
                                     bg=self.button_bg, fg=self.fg_color)
        self.download_btn.pack(side="left")

        main_container = tk.Frame(self, bg=self.bg_color)
        main_container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(main_container, bg=self.bg_color, highlightthickness=0)
        self.scroll_y = tk.Scrollbar(main_container, orient="vertical", command=self.canvas.yview,
                                     bg=self.scrollbar_bg, troughcolor=self.bg_color)
        self.scroll_x = tk.Scrollbar(main_container, orient="horizontal", command=self.canvas.xview,
                                     bg=self.scrollbar_bg, troughcolor=self.bg_color)

        self.frame = tk.Frame(self.canvas, bg=self.bg_color)

        self.canvas.configure(yscrollcommand=self.scroll_y.set, xscrollcommand=self.scroll_x.set)
        self.scroll_y.pack(side="right", fill="y")
        self.scroll_x.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.canvas_window = self.canvas.create_window((0,0), window=self.frame, anchor="nw")
        self.frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", self.on_canvas_configure)
        self.bind_mousewheel_scrolling()

        status_bar = tk.Label(self, textvariable=self.status_var, bd=1, relief="sunken", anchor="w",
                              bg=self.bg_color, fg=self.fg_color)
        status_bar.pack(side="bottom", fill="x")

    def detect_system_theme(self):
        system = platform.system()
        try:
            if system == "Windows":
                import winreg
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                         r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
                    value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                    return value == 0
                except Exception:
                    return False
            elif system == "Darwin":
                result = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'],
                                        capture_output=True, text=True)
                return result.returncode == 0
            elif system == "Linux":
                desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
                if 'cinnamon' in desktop:
                    try:
                        result = subprocess.run(['gsettings', 'get', 'org.cinnamon.desktop.interface', 'gtk-theme'],
                                                 capture_output=True, text=True)
                        return 'dark' in result.stdout.lower()
                    except Exception:
                        pass
                if 'gnome' in desktop or 'unity' in desktop:
                    try:
                        result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'],
                                                 capture_output=True, text=True)
                        return 'dark' in result.stdout.lower()
                    except Exception:
                        pass
                if 'kde' in desktop:
                    try:
                        result = subprocess.run(['kreadconfig5', '--group', 'General', '--key', 'ColorScheme'],
                                                 capture_output=True, text=True)
                        return 'dark' in result.stdout.lower()
                    except Exception:
                        pass
        except Exception:
            pass
        return False

    def setup_theme(self):
        if getattr(self, "dark_mode", False):
            self.bg_color = "#2e2e2e"
            self.fg_color = "#ffffff"
            self.entry_bg = "#404040"
            self.button_bg = "#505050"
            self.scrollbar_bg = "#606060"
            self.frame_border = "#505050"
            self.dialog_bg = "#2e2e2e"
            self.dialog_fg = "#ffffff"
            self.dialog_button_bg = "#505050"
            self.readonly_entry_bg = "#404040"
        else:
            self.bg_color = "#f0f0f0"
            self.fg_color = "#000000"
            self.entry_bg = "#ffffff"
            self.button_bg = "#e0e0e0"
            self.scrollbar_bg = "#c0c0c0"
            self.frame_border = "#c0c0c0"
            self.dialog_bg = "#f0f0f0"
            self.dialog_fg = "#000000"
            self.dialog_button_bg = "#e0e0e0"
            self.readonly_entry_bg = "#ffffff"

        self.configure(bg=self.bg_color)
        try:
            style = ttk.Style(self)
            try:
                style.theme_use('clam')
            except Exception:
                pass
            style.configure("Custom.Horizontal.TProgressbar",
                            troughcolor=self.bg_color,
                            background=self.button_bg,
                            thickness=10)
            style.map("TCombobox",
                      fieldbackground=[('readonly', self.entry_bg)],
                      foreground=[('readonly', self.fg_color)])
        except Exception:
            logger.debug("ttk.Style init failed or not supported on this platform")

    def bind_mousewheel_scrolling(self):
        self.canvas.bind_all("<MouseWheel>", self.on_mousewheel)
        self.canvas.bind_all("<Button-4>", self.on_mousewheel)
        self.canvas.bind_all("<Button-5>", self.on_mousewheel)

    def on_mousewheel(self, event):
        if getattr(event, "delta", 0) != 0:
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        elif getattr(event, "num", 0) in (4, 5):
            if event.num == 5:
                self.canvas.yview_scroll(1, "units")
            else:
                self.canvas.yview_scroll(-1, "units")
        return "break"

    def on_frame_configure(self, event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def on_canvas_configure(self, event):
        self.canvas.itemconfig(self.canvas_window, width=event.width)

    def show_start_progress(self):
        self.progress_win = tk.Toplevel(self)
        self.progress_win.title("Lade Wallpaper-Vorschau")
        self.progress_win.transient(self)
        self.progress_win.grab_set()
        self.progress_win.resizable(False, False)
        self.progress_win.configure(bg=self.dialog_bg)

        msg = ("Einen Moment bitte.\nDie Wallpaper-Vorschau wird geladen und vorbereitet.")
        msg_label = tk.Label(self.progress_win, text=msg, justify="left", padx=10, pady=10,
                             bg=self.dialog_bg, fg=self.dialog_fg)
        msg_label.pack()

        self.progress_status = tk.StringVar(value="Starte...")
        status_label = tk.Label(self.progress_win, textvariable=self.progress_status,
                               bg=self.dialog_bg, fg=self.dialog_fg)
        status_label.pack(pady=6)

        self.pb = ttk.Progressbar(self.progress_win, mode="indeterminate", length=360, style="Custom.Horizontal.TProgressbar")
        self.pb.pack(padx=10, pady=10)
        self.pb.start(10)

        self.progress_win.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()//2) - (self.progress_win.winfo_width()//2)
        y = self.winfo_y() + (self.winfo_height()//2) - (self.progress_win.winfo_height()//2)
        self.progress_win.geometry(f"+{x}+{y}")
        self.update_progress_window()

    def update_progress_window(self):
        if hasattr(self, 'progress_win') and self.progress_win.winfo_exists():
            self.progress_win.update()
            self.after(150, self.update_progress_window)

    def close_start_progress(self):
        try:
            if hasattr(self, 'pb'):
                self.pb.stop()
            if hasattr(self, 'progress_win') and self.progress_win.winfo_exists():
                self.progress_win.grab_release()
                self.progress_win.destroy()
        except Exception:
            pass

    def load_data_and_render(self):
        try:
            self.after(0, lambda: self.progress_status.set("Lade Webseite..."))
            html = safe_get(URL, stream=False, timeout=CONFIG["request_timeout"], retries=CONFIG["download_retries"]).text
            self.wallpapers = self.scrape_wallpapers(html)
            self.categories = sorted(set(w["category"] for w in self.wallpapers))
        except Exception as e:
            logger.exception("Fehler beim Laden der Webseite: %s", e)
            self.after(0, self.close_start_progress)
            self.after(0, lambda: self.show_custom_error("Fehler beim Laden", str(e)))
            return

        def apply_and_render():
            self.category_menu["values"] = ["Alle"] + self.categories
            self.category_var.set("Alle")
            self.show_images()
            self.close_start_progress()

        self.after(0, apply_and_render)

    def scrape_wallpapers(self, html):
        soup = BeautifulSoup(html, "html.parser")
        wallpapers = []
        current_cat = "Allgemein"
        for el in soup.find_all(["h2", "h3", "img"]):
            if el.name in ["h2", "h3"]:
                current_cat = el.get_text(strip=True) or current_cat
            elif el.name == "img":
                src = el.get("src")
                if not src:
                    continue
                parent = el.find_parent("a")
                full = parent["href"] if parent and parent.has_attr("href") else src
                wallpapers.append({
                    "title": el.get("alt", "") or "",
                    "thumb": src,
                    "full": full,
                    "category": current_cat
                })
        return wallpapers

    def show_images(self, event=None):
        for widget in self.frame.winfo_children():
            widget.destroy()
        self.selected.clear()
        self._cancel_all_thumb_futures()

        cat = self.category_var.get() or "Alle"
        query = (self.search_var.get() or "").lower().strip()

        items = [w for w in self.wallpapers
                 if (cat == "Alle" or w["category"] == cat)
                 and (query == "" or query in (w["title"] or "").lower())]

        cols = 5
        for i in range(cols):
            self.frame.columnconfigure(i, weight=1)

        for i, w in enumerate(items):
            frame = tk.Frame(self.frame, bd=1, relief="solid", bg=self.bg_color, highlightbackground=self.frame_border)
            frame.grid(row=i//cols, column=i%cols, padx=10, pady=10, sticky="nsew")

            pil_placeholder = PLACEHOLDER_PIL.copy()
            tk_placeholder = ImageTk.PhotoImage(pil_placeholder)
            img_lbl = tk.Label(frame, image=tk_placeholder, bg=self.bg_color)
            img_lbl.image = tk_placeholder
            img_lbl.pack()

            title_label = tk.Label(frame, text=(w["title"] or "")[:50], wraplength=200,
                                   bg=self.bg_color, fg=self.fg_color)
            title_label.pack()

            var = tk.BooleanVar()
            chk = tk.Checkbutton(frame, text="Auswählen", variable=var,
                                 bg=self.bg_color, fg=self.fg_color,
                                 selectcolor=self.button_bg,
                                 command=lambda v=var, url=w["full"]: self.toggle_select(v, url))
            chk.pack()

            btns = tk.Frame(frame, bg=self.bg_color)
            btns.pack(pady=(6,0))
            preview_btn = tk.Button(btns, text="Vorschau", bg=self.button_bg, fg=self.fg_color,
                                    command=partial(self.open_preview, w))
            preview_btn.pack(side="left", padx=(0,6))
            set_btn = tk.Button(btns, text="Als Hintergrund setzen", bg=self.button_bg, fg=self.fg_color,
                                command=partial(self._download_and_set, w, None if True else None))
            # Note: partial used differently below in set-as-wallpaper prompt; here keep a placeholder or use prompt
            set_btn.configure(command=partial(self.set_as_wallpaper_prompt, w))
            set_btn.pack(side="left")

            future = self.thumb_executor.submit(self._load_thumbnail_task, w["thumb"], PLACEHOLDER_SIZE)
            self._thumb_futures[future] = (img_lbl, w["thumb"])
            future.add_done_callback(self._on_thumb_loaded)

        self.status_var.set(f"{len(items)} Bilder gefunden (Kategorie: {cat}, Suchbegriff: '{query}')")

    def _cancel_all_thumb_futures(self):
        self._thumb_futures.clear()

    def _load_thumbnail_task(self, url, size):
        try:
            cached, meta = THUMB_CACHE.get(url)
            headers = THUMB_CACHE.get_headers_for(url)
            if cached:
                try:
                    r = safe_get(url, stream=True, timeout=CONFIG["request_timeout"], headers=headers, retries=CONFIG["download_retries"])
                    if r.status_code == 304:
                        return cached
                    else:
                        data = r.content
                        THUMB_CACHE.put(url, data, r)
                        return data
                except Exception:
                    return cached
            else:
                r = safe_get(url, stream=True, timeout=CONFIG["request_timeout"], retries=CONFIG["download_retries"])
                data = r.content
                THUMB_CACHE.put(url, data, r)
                return data
        except Exception as e:
            logger.debug("Thumbnail-Ladefehler %s: %s", url, e)
            return None

    def _on_thumb_loaded(self, future):
        try:
            result = future.result()
        except Exception as e:
            logger.debug("Thumb future exception: %s", e)
            return

        mapping = self._thumb_futures.pop(future, None)
        if mapping is None:
            return
        img_lbl, url = mapping
        if not result:
            return

        def apply_image():
            try:
                pil = Image.open(BytesIO(result)).convert("RGBA")
                pil = ImageOps.contain(pil, PLACEHOLDER_SIZE)
                tkimg = ImageTk.PhotoImage(pil)
                img_lbl.configure(image=tkimg)
                img_lbl.image = tkimg
            except Exception as e:
                logger.debug("Fehler beim Anwenden des Thumbnails: %s", e)
        self.after(0, apply_image)

    def toggle_select(self, var, url):
        if var.get():
            self.selected.add(url)
        else:
            self.selected.discard(url)

    def select_all(self):
        for child in self.frame.winfo_children():
            for w in child.winfo_children():
                if isinstance(w, tk.Checkbutton):
                    try:
                        w.select()
                    except Exception:
                        pass

    def unselect_all(self):
        for child in self.frame.winfo_children():
            for w in child.winfo_children():
                if isinstance(w, tk.Checkbutton):
                    try:
                        w.deselect()
                    except Exception:
                        pass

    def open_preview(self, wallpaper):
        dialog = tk.Toplevel(self)
        dialog.title(wallpaper.get("title") or "Vorschau")
        dialog.transient(self)
        dialog.configure(bg=self.dialog_bg)
        dialog.geometry("900x600")
        lbl = tk.Label(dialog, text="Lade...", bg=self.dialog_bg, fg=self.dialog_fg)
        lbl.pack(expand=True)
        def task():
            try:
                r = safe_get(wallpaper["full"], stream=True, retries=CONFIG["download_retries"])
                data = r.content
                pil = Image.open(BytesIO(data)).convert("RGBA")
                pil.thumbnail((880, 560))
                tk_img = ImageTk.PhotoImage(pil)
                def apply():
                    lbl.configure(image=tk_img, text="")
                    lbl.image = tk_img
                self.after(0, apply)
            except Exception as e:
                logger.debug("Preview load failed: %s", e)
                def apply_err():
                    lbl.configure(text="Vorschau konnte nicht geladen werden", fg="#ff4444")
                self.after(0, apply_err)
        threading.Thread(target=task, daemon=True).start()

    def save_selected(self):
        if not self.selected:
            self.show_custom_error("Keine Auswahl", "Bitte zuerst Bilder auswählen.")
            return

        folder = self.ask_directory()
        if not folder:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Bilder werden gespeichert")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=self.dialog_bg)

        lbl = tk.Label(dialog, text=f"{len(self.selected)} Bilder werden gespeichert...", bg=self.dialog_bg, fg=self.dialog_fg, padx=20, pady=10)
        lbl.pack()

        progress = ttk.Progressbar(dialog, mode="determinate", length=420, style="Custom.Horizontal.TProgressbar")
        progress.pack(padx=20, pady=(0,8))
        progress["maximum"] = len(self.selected)

        info_var = tk.StringVar(value="")
        info_lbl = tk.Label(dialog, textvariable=info_var, bg=self.dialog_bg, fg=self.dialog_fg)
        info_lbl.pack()

        cancel_btn = tk.Button(dialog, text="Abbrechen", bg=self.dialog_button_bg, fg=self.dialog_fg,
                               command=lambda: self._download_cancel.set())
        cancel_btn.pack(pady=(8,12))

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()//2) - (dialog.winfo_width()//2)
        y = self.winfo_y() + (self.winfo_height()//2) - (dialog.winfo_height()//2)
        dialog.geometry(f"+{x}+{y}")

        urls = list(self.selected)
        self._download_cancel.clear()
        saved_count = 0
        errors = []

        def download_worker(url):
            try:
                for attempt in range(CONFIG["download_retries"] + 1):
                    try:
                        r = safe_get(url, stream=True, retries=0, timeout=CONFIG["request_timeout"])
                        break
                    except Exception:
                        time.sleep(0.4)
                else:
                    raise RuntimeError("Download retries exhausted")
                filename = os.path.basename(url.split("?")[0]) or f"image_{url_to_hash(url)[:8]}.jpg"
                outpath = os.path.join(folder, filename)
                with open(outpath, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if self._download_cancel.is_set():
                            return {"url": url, "ok": False, "error": "abgebrochen"}
                        if chunk:
                            f.write(chunk)
                logger.info("Datei gespeichert: %s", outpath)
                return {"url": url, "ok": True, "path": outpath}
            except Exception as e:
                logger.exception("Fehler beim Download %s: %s", url, e)
                return {"url": url, "ok": False, "error": str(e)}

        futures = [self.download_executor.submit(download_worker, u) for u in urls]

        def poll_results():
            nonlocal saved_count, errors
            done_count = sum(1 for f in futures if f.done())
            progress["value"] = done_count
            info_var.set(f"{done_count}/{len(futures)} abgeschlossen")
            if self._download_cancel.is_set():
                info_var.set("Abbruch angefordert...")
            if all(f.done() for f in futures):
                for f in futures:
                    res = f.result()
                    if res.get("ok"):
                        saved_count += 1
                    else:
                        errors.append(res)
                dialog.destroy()
                summary = f"{saved_count} von {len(futures)} Bilder erfolgreich gespeichert in:\n{folder}"
                if errors:
                    summary += "\n\nFehler:\n" + "\n".join(f"{e['url']}: {e.get('error')}" for e in errors[:10])
                self.show_custom_message("Fertig", summary)
                self.status_var.set(f"{saved_count} Bilder gespeichert.")
                return
            else:
                self.after(300, poll_results)

        self.after(300, poll_results)

    def ask_directory(self):
        dialog = tk.Toplevel(self)
        dialog.title("Zielordner wählen")
        dialog.transient(self)
        dialog.grab_set()
        dialog.geometry("640x440")
        dialog.configure(bg=self.dialog_bg)

        pictures_dir = os.path.expanduser("~/Bilder")
        if not os.path.exists(pictures_dir):
            pictures_dir = os.path.expanduser("~")
        current_path = pictures_dir
        selected_path = None

        main_frame = tk.Frame(dialog, bg=self.dialog_bg)
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(main_frame, text="Aktueller Pfad:", bg=self.dialog_bg, fg=self.dialog_fg).pack(anchor="w")
        path_var = tk.StringVar(value=current_path)
        path_entry = tk.Entry(main_frame, textvariable=path_var, state="readonly",
                             bg=self.readonly_entry_bg, fg=self.dialog_fg, readonlybackground=self.readonly_entry_bg)
        path_entry.pack(fill="x", pady=(4, 8))

        list_frame = tk.Frame(main_frame, bg=self.dialog_bg)
        list_frame.pack(fill="both", expand=True)
        scrollbar = tk.Scrollbar(list_frame, bg=self.scrollbar_bg, troughcolor=self.bg_color, activebackground=self.button_bg)
        scrollbar.pack(side="right", fill="y")
        dir_list = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, bg=self.entry_bg, fg=self.dialog_fg,
                              selectbackground=self.button_bg, highlightbackground=self.frame_border, activestyle='none')
        dir_list.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=dir_list.yview)

        def update_list():
            nonlocal current_path
            dir_list.delete(0, tk.END)
            try:
                parent = os.path.dirname(current_path)
                if parent and parent != current_path:
                    dir_list.insert(tk.END, "..")
                items = os.listdir(current_path)
                dirs = [it for it in items if os.path.isdir(os.path.join(current_path, it))]
                for d in sorted(dirs):
                    dir_list.insert(tk.END, d)
                path_var.set(current_path)
            except PermissionError:
                path_var.set("Zugriff verweigert")
            except Exception as e:
                logger.debug("Update List error: %s", e)
                path_var.set(current_path)

        def on_double_click(event):
            nonlocal current_path
            sel = dir_list.curselection()
            if sel:
                val = dir_list.get(sel[0])
                if val == "..":
                    current_path = os.path.dirname(current_path)
                else:
                    current_path = os.path.join(current_path, val)
                update_list()

        dir_list.bind("<Double-Button-1>", on_double_click)

        btn_frame = tk.Frame(main_frame, bg=self.dialog_bg)
        btn_frame.pack(fill="x", pady=(8,0))
        def on_cancel():
            nonlocal selected_path
            selected_path = None
            dialog.destroy()
        def on_ok():
            nonlocal selected_path
            selected_path = current_path
            dialog.destroy()

        cancel_btn = tk.Button(btn_frame, text="Abbrechen", command=on_cancel,
                              bg=self.dialog_button_bg, fg=self.dialog_fg, width=10)
        cancel_btn.pack(side="right", padx=(8,0))
        ok_btn = tk.Button(btn_frame, text="OK", command=on_ok,
                          bg=self.dialog_button_bg, fg=self.dialog_fg, width=10)
        ok_btn.pack(side="right")

        update_list()
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()//2) - (dialog.winfo_width()//2)
        y = self.winfo_y() + (self.winfo_height()//2) - (dialog.winfo_height()//2)
        dialog.geometry(f"+{x}+{y}")
        dialog.wait_window(dialog)
        return selected_path

    def show_custom_message(self, title, message):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=self.dialog_bg)
        tk.Label(dialog, text=message, justify="left", bg=self.dialog_bg, fg=self.dialog_fg, padx=16, pady=12).pack()
        ok_btn = tk.Button(dialog, text="OK", command=dialog.destroy, bg=self.dialog_button_bg, fg=self.dialog_fg, width=10)
        ok_btn.pack(pady=(8,12))
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()//2) - (dialog.winfo_width()//2)
        y = self.winfo_y() + (self.winfo_height()//2) - (dialog.winfo_height()//2)
        dialog.geometry(f"+{x}+{y}")
        dialog.wait_window(dialog)

    def show_custom_error(self, title, message):
        dialog = tk.Toplevel(self)
        dialog.title(title)
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=self.dialog_bg)
        tk.Label(dialog, text="⚠️", font=("Arial", 16), bg=self.dialog_bg, fg="#ff4444").pack(pady=(8,0))
        tk.Label(dialog, text=message, justify="left", bg=self.dialog_bg, fg=self.dialog_fg, padx=16, pady=8).pack()
        ok_btn = tk.Button(dialog, text="OK", command=dialog.destroy, bg=self.dialog_button_bg, fg=self.dialog_fg, width=10)
        ok_btn.pack(pady=(8,12))
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()//2) - (dialog.winfo_width()//2)
        y = self.winfo_y() + (self.winfo_height()//2) - (dialog.winfo_height()//2)
        dialog.geometry(f"+{x}+{y}")
        dialog.wait_window(dialog)

    def set_as_wallpaper_prompt(self, wallpaper):
        dialog = tk.Toplevel(self)
        dialog.title("Als Hintergrund setzen")
        dialog.transient(self)
        dialog.grab_set()
        dialog.resizable(False, False)
        dialog.configure(bg=self.dialog_bg)

        tk.Label(dialog, text=f"Als Hintergrund setzen: {wallpaper.get('title')}", bg=self.dialog_bg, fg=self.dialog_fg, padx=10, pady=10).pack()
        tk.Label(dialog, text="Herunterladen und setzen?", bg=self.dialog_bg, fg=self.dialog_fg).pack()

        btn_frame = tk.Frame(dialog, bg=self.dialog_bg)
        btn_frame.pack(pady=(8,10))
        cancel_btn = tk.Button(btn_frame, text="Abbrechen", command=dialog.destroy, bg=self.dialog_button_bg, fg=self.dialog_fg, width=10)
        cancel_btn.pack(side="right", padx=(8,0))
        ok_btn = tk.Button(btn_frame, text="OK", command=lambda: self._download_and_set(wallpaper, dialog), bg=self.dialog_button_bg, fg=self.dialog_fg, width=10)
        ok_btn.pack(side="right")

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width()//2) - (dialog.winfo_width()//2)
        y = self.winfo_y() + (self.winfo_height()//2) - (dialog.winfo_height()//2)
        dialog.geometry(f"+{x}+{y}")
        dialog.wait_window(dialog)

    def _download_and_set(self, wallpaper, parent_dialog):
        """
        Lädt das full-image temporär herunter, speichert es und versucht, es als Wallpaper zu setzen.
        Zeigt anschließend Erfolg oder detailierte Fehlermeldung im Dialog an.
        """
        if parent_dialog:
            parent_dialog.destroy()

        try:
            r = safe_get(wallpaper["full"], stream=True, retries=CONFIG.get("download_retries", 2))
            data = r.content
        except Exception as e:
            logger.exception("Download für Set-Wallpaper fehlgeschlagen: %s", e)
            self.show_custom_error("Fehler", f"Herunterladen fehlgeschlagen:\n{e}")
            return

        try:
            tmp_dir = os.path.expanduser("~/.cache/guideos_wallpapers/tmp")
            ensure_dir(tmp_dir)
            fname = os.path.join(tmp_dir, os.path.basename(wallpaper["full"].split("?")[0]) or f"wp_{url_to_hash(wallpaper['full'])[:8]}.jpg")
            with open(fname, "wb") as f:
                f.write(data)
        except Exception as e:
            logger.exception("Datei schreiben fehlgeschlagen: %s", e)
            self.show_custom_error("Fehler", f"Datei konnte nicht gespeichert werden:\n{e}")
            return

        ok, err = set_wallpaper(fname)
        if ok:
            self.show_custom_message("Fertig", "Hintergrundbild gesetzt.")
        else:
            msg = f"Hintergrund konnte nicht gesetzt werden. Datei wurde gespeichert: {fname}"
            if err:
                msg += "\n\nFehler:\n" + err
                logger.warning("set_wallpaper failed: %s", err)
            self.show_custom_error("Fehler", msg)

    def _on_close(self):
        try:
            self.thumb_executor.shutdown(wait=False)
        except Exception:
            pass
        try:
            self.download_executor.shutdown(wait=False)
        except Exception:
            pass
        self.destroy()

# --- main ---
if __name__ == "__main__":
    app = WallpaperApp()
    app.mainloop()
