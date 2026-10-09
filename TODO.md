# Sir Magick – To-do-Liste

Ziel: Ein Discord-Bot im Docker-Container, der Bilder aus dem Chat oder einer URL bearbeitet und zurückpostet.

## Festgelegte Grundlagen

- [x] Programmiersprache: Python (lokal verfügbar: Python 3.12.10).
- [x] Serverbetrieb ohne GPU: Erkennung und Verarbeitung laufen auf der CPU.
- [x] GIFs als statische Bilder behandeln; Animationen ignorieren und den ersten Frame verwenden.
- [x] Bei mehreren Personen alle erkannten Personen bearbeiten.
- [x] Bei fehlender geeigneter Erkennung für `chudthor` oder `fatmagic` eine Fehlermeldung senden und den Auftrag abbrechen.
- [x] Feste Effektstärke verwenden; keine Stärke als Befehlsparameter anbieten.
- [x] Ergebnisse erneut als Eingabe zulassen: Nutzer können ein verarbeitetes Bild mit einem weiteren Befehl nochmals bearbeiten lassen.
- [ ] Erkennungsmodelle einmal beim Start laden und für weitere Bilder wiederverwenden.
- [ ] Erkennung auf verkleinerten Bildern prüfen und Koordinaten auf die Originalgröße übertragen.
- [ ] Zunächst einen Bildauftrag gleichzeitig verarbeiten; weitere Aufträge warten in einer begrenzten Warteschlange.

## 1. Erkennung lokal entwickeln

Stand: Lokales Erkennungsmodul implementiert und auf 17 Beispielbildern ausgeführt. Sechs Tests sowie ein echter Fehler-/Fortsetzungslauf bestehen. Gruppenabdeckung und Personenmasken bleiben offen; siehe README.

- [x] Erste Beispielbilder unter `images/face`, `images/halfbody` und `images/fullbody` sammeln.
- [ ] Beispielbilder visuell prüfen und Abdeckung für mehrere Personen, seitliche Ansichten und Bilder ohne Personen ergänzen.
- [x] GIFs wie statische Bilder behandeln: ersten Frame laden und Animationen ignorieren (getestet).
- [x] `.url`-Dateien beim Einlesen überspringen.
- [x] Gesichtserkennung mit Merkmalspunkten für Kontur, Augen, Nase und Mund ausprobieren.
- [x] Körpererkennung mit Haltungspunkten ausprobieren.
- [ ] Erkennung in Gruppen verbessern und prüfen, welche kleinen oder verdeckten Personen fehlen.
- [ ] Für genaue Körperkonturen zusätzlich Personenmasken prüfen; Haltungspunkte allein liefern keine Kontur.
- [x] Erkannte Gesichts- und Körperpunkte auf Kontrollbildern sichtbar machen.
- [ ] Personenmasken auf Kontrollbildern sichtbar machen, sobald Maskenerkennung ergänzt ist.
- [x] Verarbeitung aller erkannten Personen implementieren; bei fehlender geeigneter Erkennung Auftrag mit Fehlermeldung beenden (lokaler Batchlauf geprüft).

## 2. Transformationslogik entwickeln

- [ ] Pipeline aufbauen: Bild laden → erkennen → Transformation berechnen → verformen → speichern.
- [ ] Erkennung und Effekte getrennt implementieren, damit Effekte dieselben Erkennungsdaten verwenden können.
- [x] Ersten lokalen `chudthor`-Entwurf implementieren: Gesicht vergrößern, leicht viereckig formen und Augen, Mund sowie Nase verkleinern und zur Mitte rücken.
- [x] 14 Beispielergebnisse und Vorher-nachher-Übersicht unter `examples/chudthor/` ablegen.
- [x] Optik von `chudthor` anhand der Beispiele mit dem Nutzer abstimmen: genau so beibehalten.
- [ ] Wiederholte Anwendung robuster machen: stark verformte Ergebnisse werden teilweise nicht mehr als Gesicht erkannt.
- [x] Separaten `warpface`-Prototyp entwickeln: Kopfmaske, Kopf als Ganzes vergrößern, äußere Kontur leicht kantiger formen und einzelne Merkmale lokal um ihre eigene Mitte verkleinern.
- [x] Bei der lokalen Merkmalsverkleinerung die umgebenden Originalpixel in die Übergangsfläche ziehen, statt freie Stellen mit Hautpatches zu füllen.
- [ ] Neue `warpface`-Beispiele mit dem Nutzer abstimmen; Kopfmasken und Übergänge bei schwierigen Bildern prüfen.
- [x] 14 aktuelle `warpface`-Beispiele unter `examples/warpface/` exportieren und einen zweiten Durchlauf auf einem bereits bearbeiteten Porträt erfolgreich prüfen.
- [x] Bisherigen Effekt samt Befehl und Beispielen in `warpface` umbenennen.
- [x] Neuen, separaten `blockface`-Entwurf anhand von `example.jpg` entwickeln: rechteckigerer Kopf, proportional kleine Merkmale, Verteilung der Gesichtsfläche über ein Dreiecksnetz.
- [x] 14 neue `blockface`-Beispiele exportieren und geometrische Tests ergänzen; insgesamt 18 Tests bestehen.
- [x] Frühere `blockface`-Netzvariante beurteilen und durch den einfacheren Ansatz mit äußerem Hautstreifen ersetzen.
- [x] `blockface` erneut vereinfachen: keine Kopfvergrößerung oder Collage; innere Gesichtsfläche einheitlich auf 84 Prozent skalieren, nur den äußeren Hautstreifen bis zur unveränderten Kontur strecken.
- [x] Frühere Netz-Beispiele als `examples/blockface-mesh/` aufbewahren; 14 aktuelle Beispiele und 17 bestehende Tests prüfen.
- [x] Aktuelle `blockface`-Variante mit dem Nutzer abstimmen: freigegeben, vorerst genau so beibehalten; rechteckige Kontur zurückstellen.
- [ ] Übergänge zum Hintergrund und Lücken durch die Verformung behandeln.
- [ ] `fatmagic`: Gesicht und Körper leicht verzerren und kantig wie Minecraft formen.
- [ ] Effektstärken anhand der Beispielbilder abstimmen.
- [x] `deepfry`: Kontrast, Sättigung, Schärfung, Rauschen und Kompressionsartefakte kombinieren; benötigt keine Erkennung.
- [x] Pro Deepfry-Auftrag zufällig ein bis zwei gezeichnete Smilies oder Schriftzüge (`100%!!`, `xD`) einfügen und mitkomprimieren.
- [x] Deepfry auf allen 17 Bildern ausführen, Beispiele ablegen, Alpha und Wiederholung prüfen; insgesamt 21 Tests bestehen.
- [ ] Laufzeit und Speicherbedarf auf der Server-CPU messen und Bildgrößen sowie Modelle entsprechend abstimmen.

## 3. Discord anbinden

- [ ] Bot anlegen, auf einen Testserver einladen und Rechte sowie Zugriff auf Nachrichteninhalte konfigurieren.
- [x] Token sicher über eine Umgebungsvariable laden und aus dem Repository heraushalten.
- [x] `@sirmagick [command]`: letztes geeignetes Bild im Kanal verwenden; Suchgrenze und Auswahlregel festlegen.
- [x] `@sirmagick [command] [imageurl]`: Bild von der angegebenen URL verwenden.
- [x] Downloads mit Größenlimit und Zeitlimit absichern; interne Netzwerkziele auch bei Weiterleitungen sperren.
- [x] Bildformat anhand des Inhalts und Bildabmessungen prüfen.
- [x] Verarbeitungsstatus anzeigen und Ergebnis als Datei im selben Kanal posten.
- [x] Hilfe und verständliche Fehlermeldungen ergänzen; eigene Bot-Nachrichten ignorieren.
- [x] Eigene Nachrichten lösen keine Aufträge aus, ihre Bildanhänge dürfen jedoch als Eingabe für einen neuen Nutzerauftrag dienen.
- [x] Gleichzeitige Aufträge begrenzen, begrenzte Warteschlange und Nutzer-Cooldown ergänzen.
- [x] Warteschlangen-Worker nach Fehlern zuverlässig freigeben und den nächsten Auftrag starten; Verarbeitungszeit begrenzen.
- [x] Temporäre Bilder nach Erfolg oder Fehler entfernen.


Implementierung offline geprüft (28 Tests). Live-Test mit Discord-Token und Serverrechten steht noch aus; Anleitung: `DISCORD.md`.

## 4. Docker und Betrieb

- [ ] Dockerfile inklusive Erkennungsmodellen und Bibliotheken erstellen.
- [ ] Container ohne Root-Rechte betreiben.
- [ ] Compose-Datei mit Konfiguration, Neustartregel und Ressourcenlimits erstellen.
- [ ] `.env.example`, `.gitignore` und `.dockerignore` ergänzen.
- [ ] Fehler und Laufzeiten protokollieren, ohne Token oder Bildinhalte zu loggen.
- [ ] Installation, Befehle und Updates dokumentieren.
- [ ] Auf dem Docker-Server Bilder, Fehlerfälle, parallele Anfragen und Neustarts prüfen.

## Meilensteine

1. Gesichtsmerkmale und Körperbereiche auf einem lokalen Kontrollbild markieren.
2. `chudthor` lokal mit reproduzierbarer Transformationslogik umsetzen.
3. `fatmagic` ergänzen; `deepfry` kann unabhängig davon entstehen.
4. Funktionierende Bildverarbeitung an Discord anbinden.
5. Docker-Betrieb und Belastungsprüfung abschließen.

Ursprüngliche Ideen: `functionality.txt`.
