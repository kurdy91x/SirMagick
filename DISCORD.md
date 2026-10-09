# Discord-Bot starten

1. Abhängigkeiten installieren:

   ```powershell
   python -m pip --python .venv install -r requirements.txt
   ```

2. Im [Discord Developer Portal](https://discord.com/developers/applications) eine Anwendung mit Bot anlegen. Unter **Bot → Privileged Gateway Intents** den **Message Content Intent** aktivieren. Den Bot-Token in eine lokale `.env` eintragen. Dazu `.env.example` kopieren; die echte `.env` bleibt außerhalb von Git. Token nicht in Chats posten.

3. Unter **OAuth2 → URL Generator** die Scopes `bot` und `applications.commands` wählen. Benötigte Rechte: 
View Channels, 
Read Message History, 
Send Messages und 
Attach Files. Mit der erzeugten URL den Bot auf den Server einladen. Für Threads zusätzlich Send Messages in Threads erlauben.

4. Optional `ALLOWED_GUILD_IDS` und `ALLOWED_CHANNEL_IDS` in `.env` setzen (mehrere IDs durch Kommas trennen). Leer bedeutet alle erreichbaren Server bzw. Kanäle. Direktnachrichten werden ignoriert.

5. Starten:

   ```powershell
   .venv\Scripts\python.exe -m sirmagick bot
   ```

Modelle müssen für Gesichtseffekte bereits unter `models/` liegen. `deepfry`, `wide` sowie alle Trippy- und Euler-Modi funktionieren ohne Modelle. Modelle werden bei der ersten Gesichtsanfrage geladen und im Bildprozess wiederverwendet.

## Verwendung

Aktuelle Modi: `blockface`, `warpface`, `chudthor`, `deepfry`, `fatmagic`, `tinyface`, `bigmouth`, `googly`, `eyeswap`, `wide`, `zoom`, `tunnel`, `kaleidoscope`, `swirl`, `rgbghost`, `droste`, `complexsquare`, `complexexp`, `logpolar`, `inversion`, `sweat`, `sparkle`, `angry`, `random` und `help`. Alle funktionieren per `@sirmagick MODUS` und werden auch als Slash-Befehle registriert. `uwu` und `blush` bleiben bis zur optischen Abstimmung deaktiviert. Eine Übersicht steht in `README.md`.

Im Kanal `/` tippen und SirMagick auswählen: Discord zeigt die registrierten Befehle mit Beschreibungen. Jeder Effekt bietet die optionalen Felder `bild` (Datei hochladen) und `url`. Nur eines davon angeben; ohne beide wird das letzte Bild im Kanal verwendet. `/help` zeigt die Übersicht nur dem aufrufenden Nutzer.

Die Slash-Befehle werden beim Bot-Start global und nach der Verbindung zusätzlich einmal direkt auf jedem freigegebenen Server registriert. Reconnects lösen keine erneute Server-Registrierung aus. Nach dem Update den Bot neu starten. Die Konsole bestätigt die Registrierung pro Server oder zeigt HTTP-/Discord-Fehlercodes. Fehlen die Befehle, die Server-Einladung mit `bot` und `applications.commands` prüfen und gegebenenfalls erneut autorisieren. Nutzer benötigen im Kanal die Berechtigung **Use Application Commands**; auch Einschränkungen unter **Server Settings → Integrations → SirMagick** prüfen.

Wenn Befehle auswählbar sind, aber nicht antworten: Im Developer Portal darf für diesen Gateway-Bot keine fremde **Interactions Endpoint URL** eingetragen sein. Slash-Aufrufe sollen über die bestehende Gateway-Verbindung ankommen. Die Konsole zeigt beim Aufruf `Slash-Aufruf: /...`. Fehlt diese Meldung trotz auswählbarem Befehl, die Interactions-Einstellung und den tatsächlich gestarteten Bot prüfen. Taucht sie auf, die nachfolgende Fehlermeldung beachten. Befehle per Erwähnung funktionieren unabhängig von der Slash-Registrierung.

Ein Bild hochladen und den Bot erwähnen: `@SirMagick blockface`. Alternativ `@SirMagick droste https://example.org/bild.jpg`. Auch getipptes `@sirmagick` wird erkannt, wenn Nachrichteninhalte freigegeben sind.

Ein Anhang am Befehl gewinnt; andernfalls wird vor dem Befehl nach dem letzten Bild gesucht, standardmäßig in 50 Nachrichten. Bilder des Bots sind ebenfalls gültige Eingaben. Bot-Nachrichten selbst lösen keine Befehle aus. GIFs werden als erstes Einzelbild verarbeitet. Gesichtseffekte bearbeiten alle erkannten Gesichter.

Ein Auftrag läuft gleichzeitig, bis zu zehn weitere warten. Pro Nutzer ist ein Auftrag gleichzeitig erlaubt, zusätzlich gilt standardmäßig ein Cooldown von fünf Sekunden. Bei Download-, Verarbeitungs- oder Uploadfehlern wird der Auftrag abgebrochen und die Warteschlange läuft weiter. Das Verarbeitungszeitlimit beendet den separaten CPU-Prozess tatsächlich; der nächste Auftrag startet einen neuen Prozess.

Downloads: maximal 25 MiB, nur öffentliche HTTP(S)-Ziele, geprüfte DNS-Adressen und Weiterleitungen. Interne Netzwerkziele sind gesperrt. Bildformate und Pixelzahl werden anschließend separat geprüft. Ergebnisse werden als PNG gesendet; für zu große und vollständig deckende Bilder wird JPEG versucht. Bleibt das Ergebnis zu groß, folgt eine Fehlermeldung. Die Bildauflösung wird für das Uploadlimit nicht reduziert.

Alle Limits stehen in `.env.example`. Der effektive Uploadgrenzwert berücksichtigt zusätzlich das Serverlimit. Arbeitsdateien landen kurzzeitig in `.cache/jobs/` und werden nach dem Auftrag gelöscht; nach einem harten Programmabbruch können Reste zurückbleiben.

## Prüfen

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Für einen Live-Test: Bild mit Gesicht und `blockface`, dann das Ergebnis erneut bearbeiten; anschließend ein Bild ohne Gesicht beauftragen und danach `deepfry`. Der erste Auftrag muss fehlschlagen, der nachfolgende weiterlaufen. Ebenso mit mehreren Personen testen. Ein echter Discord-Lauf benötigt deinen lokalen Token und aktivierten Message Content Intent.

Technische Referenzen: [discord.py Einführung](https://discordpy.readthedocs.io/en/stable/intro.html), [Message Content Intent](https://discordpy.readthedocs.io/en/stable/intents.html), [aiohttp DNS-Prüfung](https://docs.aiohttp.org/en/stable/client_middleware_cookbook.html#server-side-request-forgery-protection).
