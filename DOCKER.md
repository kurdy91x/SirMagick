# Docker und Docker Hub

Ziel-Image: **`kurdy/sirmagick:latest`** auf Docker Hub. Das Image enthält Python 3.12, Bibliotheken, Code und beide Erkennungsmodelle. Es enthält keinen Token, keine Originalbilder und keine lokalen Testausgaben.

Die Dateien sind vorbereitet. Ein echter Linux-Docker-Build, Containerlauf und Upload wurden hier noch nicht ausgeführt: Auf dem Entwicklungsrechner ist Docker nicht installiert. Zunächst wird Linux auf einem Intel-/AMD-Server (amd64) verwendet.

## Image bauen und prüfen

Auf einem Rechner mit Docker Engine oder Docker Desktop und Compose v2, im Projektverzeichnis:

```sh
docker build --platform linux/amd64 -t kurdy/sirmagick:latest .
```

Der Build lädt die offiziellen Modelle und prüft die Bibliotheksimporte sowie das Laden beider CPU-Modelle. Er benötigt Internetzugriff. Abhängigkeiten werden aktuell innerhalb der Versionsbereiche aus `requirements.txt` aufgelöst.

Zum lokalen Container-Test muss der Compose-Parameter `DISCORD_TOKEN` gesetzt sein (über `.env`, Shell oder Deployment-Oberfläche). Einen bereits laufenden Bot mit demselben Token vorher beenden:

```sh
docker compose -f compose.yaml -f compose.build.yaml up -d --build
docker compose logs -f --tail=50
```

In Discord `@sirmagick help`, einen Gesichtseffekt und `deepfry` testen. Ein Bild ohne Gesicht mit `blockface` beauftragen, danach einen gültigen Folgeauftrag senden. Zum Beenden der Logansicht Strg+C drücken; der Container läuft weiter.

## Auf Docker Hub veröffentlichen

Im Konto **kurdy** ein Repository **sirmagick** anlegen. Sichtbarkeit (öffentlich/privat) dort bewusst wählen. Anmeldung erfolgt lokal im Terminal; Zugangsdaten nicht in Projektdateien schreiben.

```sh
docker login --username kurdy
docker push kurdy/sirmagick:latest
```

Für eine nachvollziehbare erste Veröffentlichung zusätzlich einen unveränderlich behandelten Versionsnamen verwenden:

```sh
docker tag kurdy/sirmagick:latest kurdy/sirmagick:0.1.0
docker push kurdy/sirmagick:0.1.0
```

Upload erst nach erfolgreichem Container-Test. Noch kein Image wurde durch diese Vorbereitung veröffentlicht.

## Auf dem Server starten

Auf dem Server wird `compose.yaml` benötigt. Docker und Compose v2 müssen installiert sein. Der Benutzer konfiguriert seinen eigenen Discord-Bot-Token über den Compose-Parameter `DISCORD_TOKEN`. Die Datei enthält dafür `DISCORD_TOKEN: "${DISCORD_TOKEN:?Bitte DISCORD_TOKEN setzen}"`. Fehlt der Wert oder ist er leer, bricht Compose vor dem Start mit einer verständlichen Meldung ab.

Bei normalem Compose eine `.env` neben `compose.yaml` anlegen (`.env.example` ist die Vorlage) und dort `DISCORD_TOKEN=DEIN_BOT_TOKEN` setzen. Alternativ den Parameter über die Shell oder in einer Stack-Oberfläche wie Portainer als Umgebungsvariable hinterlegen; dann wird keine `.env`-Datei benötigt. Alle weiteren unterstützten Parameter stehen ebenfalls unter `environment` in der Compose-Datei, jeweils mit Standardwerten. Ein Docker-Hub-Zugangstoken gehört zu `docker login`, nicht zu `DISCORD_TOKEN`.

Die Hostpfade für Modelle und Arbeitsdateien werden in Compose für den Container überschrieben. Modelle und Code müssen nicht separat auf den Server kopiert werden.

Bei einem privaten Repository vorher auf dem Server mit einem zum Lesen berechtigten Docker-Hub-Konto anmelden. Bei öffentlichem Repository ist dies für den Pull normalerweise nicht nötig.

```sh
docker compose pull
docker compose up -d
docker compose logs -f --tail=50
```

Der Container läuft als UID/GID 10001, ohne Root-Rechte und ohne veröffentlichte Ports. Er erhält standardmäßig maximal zwei CPU-Kerne Rechenzeit und 2 GiB RAM. Temporäre Bilder und Cache liegen im auf 512 MiB begrenzten `/tmp`; sie verschwinden beim Neuerstellen des Containers. Arbeitsspeicher und Zeitlimits auf dem tatsächlichen Server prüfen, besonders bei großen Bildern. Falls nötig in `.env` anpassen:

```dotenv
DOCKER_CPUS=2.0
DOCKER_MEMORY=2g
PROCESS_TIMEOUT_SECONDS=60
```

Ausgehend benötigt der Bot HTTPS/WSS auf TCP 443 und DNS; TCP 80 zusätzlich für HTTP-Bildlinks. Eingehende Firewall-Freigaben oder Router-Portweiterleitungen sind nicht nötig. Der Neustartmodus `unless-stopped` startet einen abgestürzten Container und nach einem Docker-Neustart erneut; bewusst gestoppte Container bleiben gestoppt. Eine automatische Erkennung eines hängenden Bot-Prozesses ist noch nicht implementiert.

## Updates und Betrieb

Nach Codeänderungen Image erneut bauen, testen und pushen. Auf dem Server:

```sh
docker compose pull
docker compose up -d
docker compose ps
```

`docker compose restart` allein lädt kein neues Image und übernimmt keine geänderte `.env`. Für eine feste Version in `compose.yaml` den Image-Tag von `latest` auf z. B. `0.1.0` ändern. Keine automatische Aktualisierung ungeprüfter Images eingerichtet.

Aufträge warten nur im Arbeitsspeicher. Neustart oder Update verwirft wartende Aufträge; Nutzer müssen sie dann neu senden. Logs werden auf drei Dateien zu je 10 MiB begrenzt. `docker compose down` stoppt und entfernt den Container, ohne die lokale `.env` zu löschen.

Referenz: [Docker Compose Service-Konfiguration](https://docs.docker.com/reference/compose-file/services/).
