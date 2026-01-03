# GuideOS Wallpaper-Manager

Ein grafischer Wallpaper-Browser für GuideOS und Cinnamon-basierte Systeme mit intelligentem Thumbnail-Caching und Nextcloud-Integration.

## Features

- 🖼️ **Intelligentes Caching** – Thumbnails werden lokal gespeichert, nur neue Bilder nachgeladen
- ⚡ **Asynchrones Laden** – GUI bleibt während des Ladens vollständig bedienbar
- 🔍 **Zoom-Funktion** – Vorschau mit STRG + Mausrad vergrößern/verkleinern
- 💾 **Sparsam** – Vollbilder werden nur auf Anforderung heruntergeladen
- 🎨 **Modernes GTK3-Design** – Native Linux-Desktop-Integration
- 🔄 **Automatische Aktualisierung** – Neue Wallpaper werden alle 10 Minuten erkannt

## Installation

### Als Debian-Paket (empfohlen)

```bash
# Paket bauen
dpkg-buildpackage -us -uc -b

# Paket installieren
sudo dpkg -i ../guideos-wallpaper-manager_2.2-1_all.deb
```

### Manuell

```bash
# Abhängigkeiten installieren
sudo apt install python3-gi gir1.2-gtk-3.0 python3-pil

# Skript ausführbar machen
chmod +x guideos-wallaper-manager

# Optional: Nach /usr/local/bin kopieren
sudo cp guideos-wallaper-manager /usr/local/bin/guideos-wallpaper-manager
sudo cp guideos-wallaper-manager.desktop /usr/share/applications/
```

## Verwendung

Programm starten:
```bash
guideos-wallpaper-manager
```

### Erststart

Beim ersten Start erscheint ein Hinweis über die benötigte Internetverbindung:
- **OK** → Thumbnails werden erstellt und gecacht
- **Abbrechen** → Programm wird beendet

### Bedienung

- **Thumbnail auswählen** – Klick öffnet hochauflösende Vorschau
- **Zoom** – STRG + Mausrad in der Vorschau
- **Als Hintergrund setzen** – Lädt Vollbild und setzt es als Desktop-Wallpaper
- **Download** – Speichert Vollbild an frei wählbarem Ort
- **Cache-Ordner öffnen** – Öffnet `~/.cache/guideos-wallpaper-manager-thumbs`
- **Bilder neu laden** – Aktualisiert die Wallpaper-Liste manuell

## Technische Details

### Verzeichnisse

- **Wallpaper-Quelle:** Nextcloud Public Share
- **Thumbnail-Cache:** `~/.cache/guideos-wallpaper-manager-thumbs/`
- **Ziel für Downloads:** `~/Bilder/GuideoWallpapers/` (erstellt bei Bedarf)

### Unterstützte Formate

- JPEG (`.jpg`, `.jpeg`)
- PNG (`.png`)
- WebP (`.webp`)

### Funktionsweise

1. Beim Start wird die Nextcloud-Ordnerstruktur ausgelesen
2. Für jedes Bild wird geprüft, ob ein Thumbnail im Cache existiert
3. Fehlende Thumbnails werden heruntergeladen und gecacht
4. Vollbilder werden **nur** bei expliziter Benutzeraktion geladen
5. Alle 10 Minuten erfolgt eine automatische Aktualisierung

## Systemanforderungen

- Python 3.6+
- GTK 3
- Cinnamon Desktop Environment (für Wallpaper-Funktion)
- Internetverbindung

## Abhängigkeiten

Das Debian-Paket installiert automatisch:
- `python3`
- `python3-gi`
- `python3-pil`
- `gir1.2-gtk-3.0`

## Entwicklung

**Autor:** evilware666 & Helga  
**Maintainer:** Actionschnitzel <actionschnitzel@guideos.de>  
**Version:** 2.2  
**Lizenz:** GPL-3+  
**Projekt:** [GuideOS](https://guideos.de)

## Lizenz

Dieses Programm ist freie Software. Sie können es unter den Bedingungen der GNU General Public License Version 3 (oder jeder späteren Version) weitergeben und/oder modifizieren.

Siehe [LICENSE](LICENSE) für Details.
