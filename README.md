```markdown
# GuideOS.de Wallpaper-Manager

## Übersicht
Der **GuideOS.de Wallpaper-Manager** ist ein grafisches Python/GTK-Tool für GuideOS und Cinnamon-basierte Systeme.  
Es ermöglicht die komfortable Verwaltung von Hintergrundbildern aus einem öffentlichen Nextcloud-Ordner und bietet eine benutzerfreundliche Oberfläche für Vorschau, Setzen und Download von Wallpapers.

- **Autor(en):** evilware666 & Helga  
- **Projekt:** GuideOS  
- **Version:** 1.7  
- **Letzte Änderung:** 19.12.2025  
- **Lizenz:** Frei nutzbar im Rahmen von GuideOS  

---

## Funktionen
- Laden von Wallpapers aus einem öffentlichen Nextcloud-Ordner  
- Automatische Thumbnail-Erstellung und Cache-Verwaltung  
- Asynchrones Laden (GUI bleibt bedienbar)  
- Vorschau in hoher Auflösung  
- Setzen des Wallpapers unter Cinnamon  
- Optionaler Download einzelner Bilder  

---

## Voraussetzungen
- **Linux-System** mit Cinnamon-Desktop  
- **Python 3**  
- **GTK 3** (`python3-gi`)  
- **Pillow (PIL)** für Bildbearbeitung  
- **Zenity** für Dialoge  
- **gsettings** für Hintergrundbildverwaltung  

---

## Installation
1. Skript speichern, z. B. unter `/usr/local/bin/wallpaper-manager.py`.  
2. Datei ausführbar machen:
   ```bash
   chmod +x /usr/local/bin/wallpaper-manager.py
   ```
3. Abhängigkeiten installieren:
   ```bash
   sudo apt install python3-gi python3-pil gir1.2-gtk-3.0 zenity
   ```

---

## Nutzung
Starte das Skript im Terminal:
```bash
./wallpaper-manager.py
```

### Ablauf:
- **Erster Start:** Thumbnails werden erstellt und lokal im Cache gespeichert.  
- **GUI:** Übersicht aller verfügbaren Wallpapers mit Vorschau.  
- **Aktionen:**  
  - Hintergrund setzen  
  - Wallpaper herunterladen  
  - Cache-Ordner öffnen  
  - Bilder neu laden  

---

## Hinweise
- Thumbnails werden im Cache unter `~/.cache/guideos-wallpaper-manager-thumbs` gespeichert.  
- Beim ersten Start kann die Erstellung der Vorschaubilder einige Minuten dauern.  
- Das Tool lädt Bilder aus dem lokalen Ordner `~/Bilder/GuideoWallpapers`.  
- Neue Bilder werden automatisch erkannt und verarbeitet.  

---

## Lizenz
Dieses Projekt steht unter der **GuideOS-Lizenz (frei nutzbar im Rahmen von GuideOS)**.  
Freie Nutzung, Modifikation und Weitergabe sind erlaubt.
```
