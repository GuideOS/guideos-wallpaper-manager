# README.md  
## GuideOS.de Wallpaper‑Manager  
### Version 2.8 – 01.01.2026  
**Autor(en):** evilware666 & Helga  
**Projekt:** GuideOS  
**Lizenz:** MIT  

### Beschreibung  
Grafischer Wallpaper‑Manager für **GuideOS.de**.  
Das Tool lädt Hintergrundbilder aus dem öffentlichen GuideOS.de‑Nextcloud‑Ordner, erzeugt automatisch Vorschaubilder (Thumbnails), speichert **keine Vollbilder lokal** (außer auf ausdrücklichen Wunsch) und ermöglicht das Setzen oder Herunterladen von Wallpapers über eine einsteigerfreundliche GTK‑Oberfläche.  
Neu in Version 2.8 ist eine **vollständige Kategorie‑Sortierung**

**Wichtig:**  
Alle Pfade werden automatisch von **@‑Zeichen bereinigt**, um maximale Kompatibilität mit Dateisystemen, WebDAV und Cinnamon zu gewährleisten.

---

## ✨ Hauptfunktionen

### 🌐 Online‑Wallpaper‑Integration
- Holt Bildliste direkt aus dem GuideOS.de‑Nextcloud‑WebDAV  
- Unterstützte Formate: **JPG, JPEG, PNG, WEBP**  
- Entfernt automatisch **alle @‑Zeichen**  
- Keine Vollbilder im Cache – nur Thumbnails  
- Preview‑API für schnelle Vorschau (1600×900)

### 🗂️ Kategorien‑System (NEU in 2.7)
- Automatische Erkennung von Kategorien anhand der Ordnerstruktur  
- Beispiel: `Natur/Sonnenuntergang.jpg` → Kategorie **Natur**  
- Kategorien werden im Dropdown angezeigt  
- „Alle Kategorien“ und „Sonstiges“ werden automatisch verwaltet  
- Live‑Filterung der Thumbnails nach Kategorie

### 🖼️ Thumbnail‑System
- Automatische Thumbnail‑Generierung (150×150 px)  
- Speicherung im lokalen Cache:  
  `~/.cache/guideos-wallpaper-manager-thumbs`  
- SHA‑256‑basierte Dateinamen für Kollision‑freie Zuordnung  
- Fortschrittsanzeige während des Ladens  
- Auto‑Refresh alle 10 Minuten

### 🔍 Zoombare Vorschau
- Großansicht mit **Strg + Mausrad** zoombar  
- Zoomfaktor 0.1× bis 10×  
- Flüssiges Nachskalieren via GdkPixbuf  
- **NEU:** Transparentes Dateinamen‑Overlay im Bild

### 🖥️ Hintergrund setzen
- Lädt Vollbild nur bei Bedarf herunter  
- Setzt Wallpaper über Cinnamon‑Schema:  
  `org.cinnamon.desktop.background picture-uri`

### 💾 Download‑Funktion
- „Speichern unter“-Dialog für Vollbilder  
- Lädt Originaldatei aus Nextcloud

---

## 📦 Installation

### Voraussetzungen
- Python 3  
- GTK3 + GObject Introspection  
- Requests  
- Cinnamon‑Desktop (für Hintergrund‑Setzen)

### Benötigte Pakete (Debian/Ubuntu)
```bash
sudo apt install python3-gi gir1.2-gtk-3.0 gir1.2-gdkpixbuf-2.0 python3-requests
```

### Starten
```bash
python3 wallpaper_manager.py
```

oder ausführbar machen:

```bash
chmod +x wallpaper_manager.py
./wallpaper_manager.py
```

---

## 📁 Verzeichnisse

| Zweck | Pfad |
|-------|------|
| Lokale Downloads | `~/Bilder/GuideOS-Wallpapers` |
| Thumbnail‑Cache | `~/.cache/guideos-wallpaper-manager-thumbs` |
| Erststart‑Flag | `~/.cache/guideos-wallpaper-manager-thumbs/.first_start_done` |

---

## 🧩 Code‑Struktur

| Komponente | Beschreibung |
|-----------|--------------|
| `clean_path()` | Entfernt alle @‑Zeichen aus Pfaden |
| `list_online_wallpapers()` | Holt Dateiliste aus Nextcloud |
| `extract_categories_from_files()` | Erzeugt Kategorien aus Ordnerstruktur |
| `update_category_dropdown()` | Aktualisiert Kategorie‑Dropdown |
| `filter_thumbnails_by_category()` | Filtert Thumbnails nach Kategorie |
| `download_thumbnail()` | Lädt oder cached Thumbnails |
| `download_full_image_to_path()` | Lädt Vollbilder |
| `ZoomableImage` | Zoombare Bildvorschau + Dateinamen‑Overlay |
| `WallpaperManager` | Hauptfenster, UI‑Logik, Kategorien, Preview |
| `thumb_clicked()` | Lädt große Vorschau |
| `set_wallpaper()` | Setzt Hintergrund via gsettings |
| `download_wallpaper()` | Speichern‑unter‑Dialog |

---

## ▶️ Bedienung

### Kategorien
- Dropdown oben in der Headerbar  
- Kategorien werden automatisch erkannt  
- Auswahl filtert die linke Thumbnail‑Ansicht  
- „Alle Kategorien“ zeigt alles  
- „Sonstiges“ für Dateien ohne Ordner

### Thumbnails
- Linke Seite zeigt alle passenden Bilder  
- Klick → große Vorschau  
- Statusleiste zeigt Dateinamen

### Vorschau
- Zoomen mit **Strg + Mausrad**  
- Transparenter Dateiname unten links  
- Bild wird automatisch skaliert

### Aktionen
- **Als Hintergrund setzen**  
- **Download**  
- **Cache‑Ordner öffnen**  
- **Bilder neu laden**

---

## 🔐 Besonderheiten & Sicherheit

- Speichert **niemals** Vollbilder automatisch  
- Nur Thumbnails werden gecached  
- Alle Pfade werden **@‑bereinigt**  
- Netzwerkfehler werden abgefangen und protokolliert  
- Keine externen Abhängigkeiten außer GTK & Requests

---

## 📄 Lizenz
MIT‑Lizenz — freie Nutzung, Anpassung und Weitergabe erlaubt.
