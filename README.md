```markdown
# GuideOS.de Wallpaper-Manager

## Übersicht
Der **GuideOS.de Wallpaper-Manager** ist ein grafischer Wallpaper-Browser für GuideOS und Cinnamon-basierte Systeme.  
Er lädt ausschließlich **Thumbnails** aus einem öffentlichen Nextcloud-Ordner, speichert diese dauerhaft im lokalen Cache und lädt **Vollbilder nur auf ausdrücklichen Benutzerwunsch**.  
Die Anwendung bietet eine moderne GTK-Oberfläche, Zoom-Funktion in der Vorschau, asynchrones Laden und einen Erststart-Hinweis mit Abbruchmöglichkeit.

- **Autor(en):** evilware666 & Helga  
- **Projekt:** GuideOS  
- **Version:** 2.2  
- **Letzte Änderung:** 23.12.2025  
- **Lizenz:** Frei nutzbar im Rahmen von GuideOS  

---

## Verhalten
- Beim Start erscheint ein Hinweis, dass das Programm eine Internetverbindung benötigt.  
- Der Erststart-Dialog kann mit **Abbrechen** beendet werden → Programm wird geschlossen.  
- Thumbnails werden aus dem Nextcloud-Share erzeugt und gespeichert unter:  
  `~/.cache/guideos-wallpaper-manager-thumbs`
- Thumbnails bleiben dauerhaft im Cache.  
- Beim Start:
  - Nextcloud-Ordner wird eingelesen.  
  - Für jede Datei:
    - Thumbnail vorhanden → aus Cache geladen  
    - Thumbnail fehlt → einmalig aus Nextcloud geladen  
- Vollbilder werden **nicht automatisch** heruntergeladen.  
- Vollbilder werden **nur** geladen, wenn der Benutzer:
  - „Als Hintergrund setzen“ oder  
  - „Download“  
    auswählt.  
- Vorschau nutzt die Nextcloud-Preview-API (hochauflösend, aber kein Vollbild).  
- Vorschau unterstützt **Zoom per STRG + Mausrad**.  

---

## Funktionen
- Laden von Wallpapers aus einem öffentlichen Nextcloud-Ordner (nur Meta + Thumbnails)  
- Persistenter Thumbnail-Cache  
- Nur neue Bilder werden nachgeladen  
- Asynchrones Laden (GUI bleibt bedienbar)  
- Vorschau in hoher Auflösung über Nextcloud-Preview  
- Zoom-Funktion (STRG + Mausrad)  
- Setzen des Wallpapers unter Cinnamon (lädt dann das Vollbild)  
- Optionaler Download einzelner Bilder (lädt dann das Vollbild)  
- Cache-Ordner öffnen  
- Abbruch-Button im Erststart-Dialog  

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
   mkdir -p ~/Bilder/GuideOS-Wallpapers
   ```

---

## Nutzung
Starten:
```bash
./wallpaper-manager.py
```

### Bedienung
- **Erststart-Dialog:**  
  - OK → Thumbnails werden erstellt  
  - Abbrechen → Programm beendet sich  
- **Thumbnail-Liste:**  
  - Klick auf ein Thumbnail lädt große Vorschau  
- **Vorschau:**  
  - STRG + Mausrad → Zoom  
  - Bild wird automatisch skaliert  
- **Buttons:**  
  - „Als Hintergrund setzen“ → lädt Vollbild & setzt Wallpaper  
  - „Download“ → speichert Vollbild an frei wählbarem Ort  
  - „Cache-Ordner öffnen“ → öffnet Thumbnail-Cache  
  - „Bilder neu laden“ → aktualisiert Liste  

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
