# GuideOS Wallpaper-Manager

Grafisches Python-Tool zum Anzeigen, Verwalten und Einreichen von
Wallpapers für GuideOS.

Der Wallpaper-Manager lädt Bilder von guideos.de, unterstützt lokale
Wallpapers (Datei oder Ordner) und erlaubt das direkte Einreichen
eigener Bilder über die offizielle Upload-Seite.

------------------------------------------------------------------------

## Features

-   Laden von Wallpapers von https://guideos.de\
-   Übersichtliche Thumbnail-Ansicht mit Vorschau\
-   Wallpaper als Cinnamon-Hintergrund setzen\
-   Download-Funktion für Web-Wallpapers\
-   Lokale Bilder laden (Datei oder Ordner, rekursiv)\
-   Upload-Funktion für **lokale** Wallpapers\
-   Upload nur bei Erfüllung der Richtlinien (4K, Rechteinhaber)

------------------------------------------------------------------------

## Voraussetzungen

-   Python 3\
-   GTK 3 (PyGObject)

Benötigte Pakete (Ubuntu / GuideOS):

    sudo apt install python3 python3-gi gir1.2-gtk-3.0                  python3-requests python3-bs4 python3-pil

------------------------------------------------------------------------

## Starten

    chmod +x wallpaper_manager.py
    ./wallpaper_manager.py

oder

    python3 wallpaper_manager.py

------------------------------------------------------------------------

## Nutzung

### Web-Wallpapers

Lädt automatisch alle verfügbaren Wallpapers von guideos.de.

### Lokale Wallpapers

Über „Lokale Bilder laden": - Einzelne Datei auswählen\
- Ganzen Ordner inkl. Unterordner einlesen

### Upload

-   Nur für lokal geladene Bilder aktiv\
-   Mindestauflösung: **3840×2160 (4K)**\
-   Nutzer muss Rechteinhaber sein\
-   Zustimmung zu den guideos.de-Richtlinien erforderlich

------------------------------------------------------------------------

## Speicherort

Heruntergeladene Bilder werden gespeichert in:

    ~/Bilder/GuideoWallpapers

Der Ordner wird automatisch erstellt.

------------------------------------------------------------------------

## Hinweise

-   Automatischer Upload kann fehlschlagen, wenn sich das
    Upload-Formular ändert\
-   In diesem Fall wird die Upload-Seite im Browser geöffnet\
-   Aktuell ist Cinnamon als Desktop-Umgebung vorgesehen

------------------------------------------------------------------------

## Lizenz

MIT License

------------------------------------------------------------------------

## Projekt

GuideOS\
https://guideos.de

Entwicklung: evilware666\
Umsetzung & Pflege: Helga
