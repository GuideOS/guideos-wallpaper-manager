# GuideOS.de Wallpaper-Manager

Ein grafischer Wallpaper-Manager für GuideOS und Cinnamon-basierte Systeme.
Das Tool lädt Hintergrundbilder aus einem öffentlichen Nextcloud-Ordner, erstellt automatisch Vorschaubilder (Thumbnails) und ermöglicht das Setzen oder Herunterladen von Wallpapers mit wenigen Klicks.

---

## Funktionen

* Laden von Wallpapers aus einem öffentlichen Nextcloud-Ordner
* Automatische Erstellung und Zwischenspeicherung von Thumbnails
* Schnelle Vorschau in hoher Auflösung
* Setzen des ausgewählten Bildes als Desktop-Hintergrund
* Optionaler Download einzelner Wallpapers
* Asynchrones Laden (GUI bleibt jederzeit bedienbar)
* Automatische Aktualisierung der Bildliste alle 10 Minuten
* Einsteigerfreundliche GTK-Oberfläche

---

## Erster Start

Beim ersten Start:

* werden alle verfügbaren Wallpaper-Thumbnails erzeugt
* werden die Vorschaubilder lokal zwischengespeichert
* kann der Vorgang – je nach Anzahl der Bilder – etwas Zeit benötigen

Der Thumbnail-Cache wird dauerhaft gespeichert.
Bei späteren Starts werden **nur neue Bilder** nachgeladen.

Cache-Verzeichnis:

```
~/.cache/guideos-wallpaper-manager-thumbs
```

---

## Speicherorte

* **Wallpapers:**

  ```
  ~/Bilder/GuideoWallpapers
  ```

* **Thumbnail-Cache:**

  ```
  ~/.cache/guideos-wallpaper-manager-thumbs
  ```

---

## Voraussetzungen

Benötigte Pakete:

* python3
* python3-gi
* gir1.2-gtk-3.0
* python3-requests
* python3-bs4
* python3-pil

Installation unter Debian/Ubuntu/GuideOS:

```bash
sudo apt install python3 python3-gi gir1.2-gtk-3.0 \
                 python3-requests python3-bs4 python3-pil
```

---

## Starten des Programms

Das Skript ausführbar machen:

```bash
chmod +x guideos-wallpaper-manager.py
```

Starten mit:

```bash
./guideos-wallpaper-manager.py
```

Oder über eine passende `.desktop`-Datei im Anwendungsmenü.

---

## Bedienung

1. Programm starten
2. Wallpapers werden automatisch geladen
3. Auf ein Vorschaubild klicken
4. Vorschau erscheint rechts
5. Optionen:

   * **Als Hintergrund setzen**
   * **Download** (Speicherort frei wählbar)

Zusätzlich:

* Button **„Bilder neu laden“** aktualisiert die Liste manuell
* Button **„Cache-Ordner öffnen“** öffnet den Thumbnail-Cache

---

## Unterstützte Bildformate

* JPG / JPEG
* PNG
* WEBP

---

## Technische Details

* GTK 3 Oberfläche (PyGObject)
* Asynchrones Laden mit Threads
* Thumbnail-Erzeugung mit Pillow
* Hash-basierte Thumbnail-Namen (keine Dateikonflikte)
* Hintergrund setzen über `gsettings` (Cinnamon)

---

## Einschränkungen

* Aktuell optimiert für **Cinnamon Desktop**
* Andere Desktop-Umgebungen benötigen ggf. angepasste `gsettings`-Befehle

---

## Autor

evilware666 & Helga
Projekt: GuideOS
Version: 1.7
Datum: 13.12.2025

---

## Lizenz

Frei nutzbar im Rahmen von GuideOS.
Anpassungen, Erweiterungen und Weiterverwendung sind ausdrücklich erwünscht.

---

Wenn du möchtest, erstelle ich dir als Nächstes:

* eine passende `.desktop`-Datei
* eine gekürzte README für Releases
* oder eine englische Version der README

