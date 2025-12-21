```markdown
# GuideOS.de Wallpaper-Manager

## Übersicht
Der **GuideOS.de Wallpaper-Manager** ist ein grafischer Wallpaper-Browser für GuideOS und Cinnamon-basierte Systeme.  
Er lädt ausschließlich **Thumbnails** aus einem öffentlichen Nextcloud-Ordner, speichert diese dauerhaft im lokalen Cache und lädt **Vollbilder nur auf ausdrücklichen Benutzerwunsch**.  
Die Anwendung bietet eine übersichtliche GTK-Oberfläche mit Vorschau, Hintergrund-Setzen und Download-Funktion.

- **Autor(en):** evilware666 & Helga  
- **Projekt:** GuideOS  
- **Version:** 1.8 
- **Letzte Änderung:** 21.12.2025  
- **Lizenz:** Frei nutzbar im Rahmen von GuideOS  

---

## Verhalten
- Thumbnails werden aus dem Nextcloud-Share erzeugt und gespeichert unter:  
  `~/.cache/guideos-wallpaper-manager-thumbs`
- Thumbnails bleiben dauerhaft im Cache.
- Beim Start:
  - Nextcloud-Ordner wird eingelesen.
  - Für jede Datei:
    - Thumbnail vorhanden → direkt aus Cache geladen.
    - Thumbnail fehlt → einmalig aus Nextcloud geladen.
- Vollbilder werden **nicht automatisch** heruntergeladen.
- Vollbilder werden **nur** geladen, wenn der Benutzer:
  - „Als Hintergrund setzen“ oder  
  - „Download“  
    auswählt.
- Vorschau nutzt die Nextcloud-Preview-API (hochauflösend, aber kein Vollbild).

---

## Funktionen
- Laden von Wallpapers aus einem öffentlichen Nextcloud-Ordner (nur Meta + Thumbnails)  
- Persistenter Thumbnail-Cache  
- Nur neue Bilder werden nachgeladen  
- Asynchrones Laden (GUI bleibt bedienbar)  
- Vorschau in hoher Auflösung über Nextcloud-Preview  
- Setzen des Wallpapers unter Cinnamon (lädt dann das Vollbild)  
- Optionaler Download einzelner Bilder (lädt dann das Vollbild)  

---

## Abhängigkeiten
- `python3-gi`  
- `gir1.2-gtk-3.0`  
- `python3-requests`  

Installation (Debian/Ubuntu):
```bash
sudo apt install python3-gi gir1.2-gtk-3.0 python3-requests
```

---

## Installation
1. Datei speichern, z. B. unter:
   ```
   /usr/local/bin/wallpaper-manager.py
   ```
2. Ausführbar machen:
   ```bash
   chmod +x /usr/local/bin/wallpaper-manager.py
   ```
3. Optional: Ordner für Vollbilder anlegen:
   ```bash
   mkdir -p ~/Bilder/GuideoWallpapers
   ```

---

## Nutzung
Starten:
```bash
./wallpaper-manager.py
```

### Bedienung
- **Thumbnails** erscheinen links in einer FlowBox.  
- **Klick auf ein Thumbnail:**  
  - Große Vorschau wird geladen (Nextcloud-Preview).  
  - Buttons „Als Hintergrund setzen“ und „Download“ werden aktiviert.  
- **Als Hintergrund setzen:**  
  - Vollbild wird heruntergeladen (falls nicht vorhanden).  
  - Hintergrund wird über `gsettings` gesetzt.  
- **Download:**  
  - Vollbild wird an frei wählbaren Speicherort heruntergeladen.  
- **Cache-Ordner öffnen:**  
  - Öffnet den Thumbnail-Cache im Dateimanager.  
- **Bilder neu laden:**  
  - Liest Nextcloud erneut ein und lädt neue Thumbnails nach.

---

## Hinweise
- Das Tool speichert **keine Vollbilder automatisch**, nur Thumbnails.  
- Vollbilder werden ausschließlich auf Benutzeraktion geladen.  
- Der Cache wird nie gelöscht und beschleunigt zukünftige Starts.  
- Neue Bilder im Nextcloud-Share werden automatisch erkannt.  
- Die Vorschau ist nicht das Originalbild, sondern ein hochauflösendes Preview.

---

## Lizenz
Frei nutzbar im Rahmen von GuideOS.  
Weitergabe und Modifikation sind erlaubt.
```
