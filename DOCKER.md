# Docker and Docker Hub

Image: **`kurdy/sirmagick:latest`**. It contains Python 3.12, application code, dependencies, and both official detection models. Personal photos, local previews, and tokens are excluded. A previous build and running bot were confirmed by the maintainer; Docker is unavailable on the development machine for verifying subsequent builds.

## Build and test

Use Docker Engine or Docker Desktop with Compose v2. The target is a Linux Intel/AMD server (`amd64`). From the project directory:

```sh
docker build --platform linux/amd64 -t kurdy/sirmagick:latest .
docker compose -f compose.yaml -f compose.build.yaml up -d --build
docker compose logs -f --tail=50
```

The build needs internet access to install dependencies and download models. It checks library imports, loads both CPU models, and audits application files for unexpected images and `.env`. Dependencies currently resolve within the version ranges in `requirements.txt`.

Set `DISCORD_TOKEN` through `.env`, the shell, or your deployment UI before starting. Stop other instances using the same token. Check `/help`, a face effect, and `deepfry`; follow a failed face request with a valid image request. Ctrl+C exits the log view without stopping the container.

## Publish

Create the `sirmagick` repository in the `kurdy` Docker Hub account and choose its visibility. Authenticate locally; keep credentials out of project files.

```sh
docker login --username kurdy
docker push kurdy/sirmagick:latest
docker tag kurdy/sirmagick:latest kurdy/sirmagick:0.1.0
docker push kurdy/sirmagick:0.1.0
```

Publish after a successful container test. Treat version tags as immutable. A Docker Hub access token is used by `docker login`; it is different from the Discord bot token.

## Server deployment

Copy `compose.yaml` to a server with Docker and Compose v2. Set `DISCORD_TOKEN` in a neighboring `.env`, using `.env.example` as a template, or set it through a deployment UI such as Portainer. Compose refuses to start with an empty token. Other supported settings have defaults in `compose.yaml`. Code and models are already in the image.

Private repositories require a Docker Hub login with pull access.

```sh
docker compose pull
docker compose up -d
docker compose logs -f --tail=50
```

The container runs as UID/GID 10001, without root privileges or published ports. Defaults limit it to two CPU cores and 2 GiB RAM. Temporary storage is a 512 MiB `/tmp` mount. Tune limits on the actual server for large images:

```dotenv
DOCKER_CPUS=2.0
DOCKER_MEMORY=2g
PROCESS_TIMEOUT_SECONDS=60
```

Outbound connections need HTTPS/WSS on TCP 443 and DNS; HTTP image links also need TCP 80. No incoming firewall rule or router port forwarding is required. `unless-stopped` restarts crashed containers and resumes them after Docker restarts; deliberately stopped containers remain stopped. There is no automatic hang watchdog.

## Private data and licensing

`.dockerignore` denies all files except explicit build inputs and six exact effect overlays: `shades.png`, `blunt.png`, `anime.rays.jpg`, `wasted.gta.jpg`, `youdied.souls.jpg`, and `horni.jail.jpg`, all under `sirmagick/assets/`. The Dockerfile copies them explicitly, and Setuptools packages only those asset paths. The build checks copied/installed application files against `sirmagick.asset_manifest.ALLOWED_ASSETS`, rejects other images or `.env`, and verifies each overlay exists. Temporary package build files are removed first. Official `.task` models are allowed; private originals and comparisons are excluded.

The image includes `/app/LICENSE`, `/app/THIRD_PARTY_NOTICES.md`, and `/app/licenses/Apache-2.0.txt`. MIT covers SirMagick's code; dependencies and models retain their own terms. See [third-party notices](THIRD_PARTY_NOTICES.md).

To replace an old image that contained private data:

```sh
docker build --no-cache --platform linux/amd64 -t kurdy/sirmagick:latest .
docker run --rm --entrypoint sh kurdy/sirmagick:latest -c 'find /app -type f | sort'
```

Inspect and test before pushing, then pull and recreate on the server. Rebuilding does not remove old containers, cached layers, or published tags; remove affected old versions separately. Runtime jobs use temporary storage and are not part of the built image.

## Updates and operation

After code changes, rebuild, test, and push.

All current slash commands use `sm_`, including `/sm_help` and `/sm_random`. After deploying the rebuilt image and restarting the bot, command synchronization replaces the old unprefixed names globally and in allowed guilds. Use `/sm_` to filter the Discord command menu. Mention commands such as `@sirmagick help` keep their short names.

On the server:

```sh
docker compose pull
docker compose up -d
docker compose ps
```

`docker compose restart` neither pulls a new image nor applies changed environment settings. Use `up -d --force-recreate` when explicit recreation is needed. Pin a version tag instead of `latest` for controlled upgrades. No automatic image updates are configured.

Restarts discard queued jobs. Logs rotate across three files of 10 MiB each. `docker compose down` removes the container but leaves your local `.env` intact.
