# Sir Magick

Discord-Bot mit CPU-basierter Bildverarbeitung. Aktuell implementiert sind das lokale Erkennungsmodul und die getrennten Effekte `chudthor`, `warpface` und `blockface`. Discord und weitere Effekte folgen danach.

## Deepfry

```powershell
.\.venv\Scripts\python.exe -m sirmagick deepfry images
.\.venv\Scripts\python.exe -m sirmagick.examples --effect deepfry
```

Feste Rezeptur: starke Sättigung und Kontrast, warme übersteuerte Farben, Schärfehalos, Körnung, reduzierte Farbabstufungen und zwei echte JPEG-Kompressionsdurchläufe. Pro Auftrag kommen zufällig ein bis zwei selbst gezeichnete Smilies oder Schriftzüge (`100%!!`, `xD`) hinzu. Die Sticker werden vor der letzten JPEG-Kompression aufgesetzt, damit sie ebenfalls Artefakte bekommen. Keine zusätzlichen Assets, Fonts oder Pakete sind nötig.

Der Effekt benötigt keine Personen, MediaPipe-Modelle oder GPU. Für die Effektrechnung wird intern auf maximal 1280 Pixel an der längsten Kante verkleinert; das Ergebnis erhält die ursprünglichen Abmessungen und den exakten ursprünglichen Alpha-Kanal. Bilder unter 32 Pixeln an der kurzen Kante bekommen keine Sticker. Wiederholte Anwendung ist möglich und verschlechtert das Bild weiter; die Sticker variieren pro Auftrag. Ein interner Seed dient ausschließlich reproduzierbaren Tests, die Nutzerstärke bleibt fest.

Alle 17 Beispielbilder wurden erfolgreich verarbeitet. Die reine Effektzeit mit Stickern beträgt lokal ungefähr 13–291 ms pro Bild, ohne Laden und Speichern. Beispiele: `examples/deepfry/vergleich.jpg`. Insgesamt 21 Tests bestehen, einschließlich Transparenz, Wiederholung und einem Batchlauf mit kaputter Datei, in dem der Folgeauftrag ohne Erkennungsmodelle erfolgreich verarbeitet wird.

Die Implementierung verwendet die dokumentierten [Pillow-Farb- und Kontrastfilter](https://pillow.readthedocs.io/en/stable/reference/ImageEnhance.html) sowie [JPEG-Qualität und Chroma-Subsampling](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html). Der Effekt ist eine eigene Kombination dieser Verfahren.

## Repository

Eingerichtetes Remote (`origin`): `https://gitlab.kurdy.de/kurdy/sirmagick.git`.

Git wurde lokal auf Branch `main` initialisiert. Das Remote wurde vom Nutzer eingerichtet und lokal geprüft. Remote-Änderungen lassen sich mit folgendem Befehl abrufen:

```powershell
git fetch origin
```

Vor dem ersten Push prüfen, ob das Remote bereits Commits enthält, und diese gegebenenfalls integrieren. Lokale Beispielbilder, generierte Ergebnisse, Modelle, virtuelle Umgebung und `.env` sind über `.gitignore` ausgeschlossen.

## Blockface: Gesichtsfläche verkleinern

```powershell
.\.venv\Scripts\python.exe -m sirmagick blockface images
.\.venv\Scripts\python.exe -m sirmagick.examples --effect blockface
```

Die aktuelle Optik ist vom Nutzer freigegeben und bleibt vorerst so erhalten. Die innere Gesichtsfläche wird gemeinsam auf 84 Prozent skaliert. Augen, Nase, Mund und ihre Abstände behalten dabei dieselben Proportionen. Nur der Hautstreifen zwischen dieser verkleinerten Fläche und der unveränderten äußeren Gesichtskontur wird gestreckt.

Der innere Quellbereich reicht bis 88 Prozent des Konturradius und umfasst damit ungefähr 77 Prozent der ursprünglichen Gesichtsfläche. Er wird einheitlich skaliert; der äußere Quellstreifen bildet den Übergang. Alle Pixel außerhalb der verwendeten Gesichtskontur bleiben bitgenau gleich. Hintergrund, Haare und Kopfgröße werden nicht verändert. Die Gesichtskontur folgt den erkannten Landmark-Punkten und berücksichtigt die Kopfneigung. Die rechteckigere Form ist auf Wunsch zunächst zurückgestellt.

Der Batch erzeugt 14 Ergebnisse; drei Bilder ohne erkanntes Gesicht werden abgebrochen. Aktuelle Beispiele: `examples/blockface/vergleich.jpg`. Die bisherigen Netz-Beispiele liegen als Referenz unter `examples/blockface-mesh/`. Insgesamt 17 Tests bestehen, einschließlich gleichmäßiger innerer Skalierung, unveränderter Außenpixel, monotoner Übergänge und mehrerer Gesichter.

## Warpface-Prototyp

```powershell
.\.venv\Scripts\python.exe -m sirmagick warpface images
.\.venv\Scripts\python.exe -m sirmagick.examples --effect warpface
```

`warpface` nähert zunächst die Kopfmaske anhand der Gesichtskontur und GrabCut an. Der Kopf wird als zusammenhängender Bereich um 30 Prozent vergrößert und am Hals verankert. Eine geringe Änderung der äußeren Wangenkontur macht ihn etwas kantiger; das Gesichtsinnere wird dabei nicht global verformt. Augen, Nasenspitze und Mund werden jeweils um ihre eigene Mitte auf 50 Prozent verkleinert. Die umliegenden Originalpixel werden lokal in die Übergangsfläche gezogen. Es werden keine neuen Gesichtsinhalte generiert und keine Hautpatches eingesetzt.

`examples/warpface/vergleich.jpg` zeigt die aktuelle lokale Skalierung. Unter `examples/warpface-patches/` liegt zum Vergleich der vorherige Versuch mit eingesetzter Umgebungsstruktur. `chudthor` behält seine freigegebene Optik.

Der aktuelle Batch liefert 14 Ergebnisse und drei erwartete Abbrüche ohne Gesichtserkennung. Ein zweiter Durchlauf auf dem bereits bearbeiteten frontalen Porträt `25-12-04 13-47-10 2171.jpg.warpface.png` war erfolgreich; das Ergebnis liegt unter `output-warpface-repeat/`. Das bestätigt die Wiederverwendung für dieses Beispiel, nicht für beliebig stark verfremdete Bilder.

Die Kopfmaske ist eine Annäherung, keine vollständige Haar-/Kopfsegmentierung. Bei geneigten Köpfen, Verdeckungen, überlappenden Personen und stark strukturiertem Hintergrund können Ränder auffallen. Große Köpfe können am Bildrand abgeschnitten werden; die Leinwand bleibt gleich groß. Die lokale Verkleinerung zieht Textur im unmittelbaren Umfeld mit: besonders Bart und Falten können dort sichtbar gestreckt werden. Die Optik von `warpface` ist noch zur Abstimmung offen; gleiche Bildqualität ohne jede Resampling-Änderung wird nicht garantiert.

OpenCV ist ausdrücklich in `requirements.txt` erfasst; in der aktuellen Umgebung war es bereits als MediaPipe-Abhängigkeit installiert.

## Chudthor-Beispiele

Unter `examples/chudthor/` liegen 14 bearbeitete Bilder in Originalauflösung. `vergleich.jpg` zeigt jeweils Original und Ergebnis nebeneinander. Drei der 17 Eingaben liefern kein erkanntes Gesicht und wurden wie vorgesehen abgebrochen.

```powershell
.\.venv\Scripts\python.exe -m sirmagick chudthor images
.\.venv\Scripts\python.exe -m sirmagick.examples
```

Feste Effektstärke: größeres, leicht viereckiges Gesicht und einzeln verkleinerte Augen, Nase und Mund. Textur und Transparenz werden aus dem Original übernommen. Alle erkannten Gesichter werden bearbeitet. Zeilenblöcke begrenzen den zusätzlichen Arbeitsspeicher der Verformung. Die skurrile Optik ist freigegeben; angrenzende Haare und Hintergrund werden sichtbar mitverformt.

Wiederholte Anwendung ist technisch über dieselbe Bildschnittstelle möglich, aber noch nicht zuverlässig: Das erneut eingelesene Beispiel `drache1.PNG.chudthor.png` wurde nach der starken Verformung nicht mehr als Gesicht erkannt und daher mit Fehler abgebrochen. Diese Grenze bleibt vor Abschluss des gesamten Effekts offen. Zehn Tests bestehen, einschließlich mehrerer Gesichter, Alpha-Interpolation, unverändertem Eingabebild und monotonen radialen Abbildungen.

## Installation unter Windows

Python 3.12 verwenden. Im Projektordner in einer normalen PowerShell ausführen:

```powershell
python -m venv .venv
python -m pip --python .venv install -r requirements.txt
```

Falls `.venv` bereits existiert, genügt der zweite Befehl. Eine Aktivierung der Umgebung ist nicht nötig.

## Modelle herunterladen und Erkennung starten

```powershell
.\.venv\Scripts\python.exe -m sirmagick download-models
.\.venv\Scripts\python.exe -m sirmagick detect images
```

Die Modelle werden explizit von Googles offiziellem MediaPipe-Modellspeicher nach `models/` geladen. Während der Erkennung werden keine Bilder hochgeladen; sie läuft lokal auf der CPU.

Unter `output/` entstehen Kontrollbilder mit grünen Gesichtspunkten und orangefarbenen Körpermerkmalen sowie JSON-Dateien mit Koordinaten im Originalbild. `output/report.json` enthält Ergebnisse, Fehler und Laufzeiten pro Datei sowie die Modellstartzeit.

JPG, PNG, WebP und GIF werden eingelesen. Bei GIFs wird nur der erste Frame verwendet. `.url`-Dateien werden übersprungen. Transparenz bleibt im Original erhalten und wird nur für die Erkennung auf Weiß aufgelöst.

Alle erkannten Personen werden berücksichtigt, mit einem konfigurierbaren technischen Limit von zunächst 20 Gesichtern beziehungsweise Körpern pro Bild. Die Erkennung arbeitet mit maximal 1024 Pixeln an der längsten Kante. Keine Erkennung und beschädigte Bilder führen zu einem Fehler für diese Datei; der nächste Auftrag wird weiterbearbeitet. Der Diagnosebericht bleibt verfügbar.

```powershell
# Nur Gesichtserkennung als Erfolg akzeptieren:
.\.venv\Scripts\python.exe -m sirmagick detect images/face --require face

# Kleinere Erkennungsbilder für einen Laufzeitvergleich:
.\.venv\Scripts\python.exe -m sirmagick detect images --max-side 768 --output output-small
```

Exitcodes: `0` = alle Dateien erfolgreich, `1` = mindestens eine Datei fehlgeschlagen, `2` = Start- oder Konfigurationsfehler.

## Aktueller Prüfstand

Syntax, CLI-Hilfe und Paketimporte wurden geprüft. Alle 17 aktuellen Beispielbilder lassen sich laden. Sechs Tests für Originalkoordinaten, fehlende Erkennung, GIF-Erstframe, Transparenz/Skalierung, EXIF-Ausrichtung und kaputte Dateien bestehen.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Der echte CPU-Modelllauf auf allen 17 Beispielbildern und eine visuelle Übersichtskontrolle sind abgeschlossen. Erkennung pro Bild: ungefähr 16–94 ms auf dem Entwicklungsrechner, ohne Bildladen, PNG-Ausgabe und Modellstart. Diese Werte sind keine Messung auf dem Docker-Server.

Ein zusätzlicher Lauf mit leerem Bild, beschädigter Datei und anschließend gültigem Porträt bestätigt: Beide Fehler werden gemeldet und der gültige Folgeauftrag wird verarbeitet. Der Lauf liefert wie vorgesehen Exitcode 1.

Bekannte Grenzen: In Gruppen werden nicht immer alle Personen erkannt; kleine, verdeckte und seitliche Gesichter sowie stilisierte Figuren sind schwierig. Im Anime-GIF wurde kein Gesicht erkannt, beim anderen Anime-Bild kein Körper. Ein erfolgreicher Diagnoselauf bedeutet, dass mindestens eine passende Erkennung vorliegt, nicht dass jede Person gefunden wurde. Körperpunkte liefern keine genauen Körperkonturen; Personenmasken sind noch nicht implementiert. Vor dem Körpereffekt sind Masken und bessere Gruppenabdeckung separat zu prüfen.

Die aktuellen Ergebnisse stehen in `output/report.json` und den Kontrollbildern unter `output/`. Die einmalig erzeugte Übersicht `output/contact-sheet.jpg` dient der Sichtprüfung und wird vom CLI nicht automatisch aktualisiert.

Referenzen: [MediaPipe Face Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/face_landmarker/python), [MediaPipe Pose Landmarker](https://ai.google.dev/edge/mediapipe/solutions/vision/pose_landmarker/python).

## Discord-Bot

Docker-Build, Veröffentlichung als `kurdy/sirmagick` und Serverbetrieb: [DOCKER.md](DOCKER.md). Der tatsächliche Build und Upload stehen noch aus.

Alte lokale Testläufe liegen archiviert unter `.cache/local-runs/`. Neue CLI-Läufe erzeugen ihre Ausgabeordner wie gewohnt. Originalbilder stehen in `images/`, ausgewählte Vergleiche in `examples/`. Mit `python tools/tidy_workspace.py` lassen sich neue Testläufe wieder archivieren; es werden keine Dateien gelöscht. `.dockerignore` hält Token, lokale Umgebung, Testbilder und Ausgaben aus dem Docker-Build-Kontext heraus.

Die Discord-Anbindung mit begrenzter Warteschlange, Nutzer-Cooldown und separatem CPU-Prozess ist implementiert. Einrichtung, Rechte, `.env` und Startbefehl: [DISCORD.md](DISCORD.md). Live-Test auf einem Discord-Server steht noch aus.
