# SirMagick

A CPU-only Discord image bot with face distortions, trippy transformations, complex-coordinate effects, and anime decals. No GPU required. The Docker image includes the detection models.

## Run with Docker

Image: `kurdy/sirmagick:latest` (Linux/amd64). Use [compose.yaml](compose.yaml), set your own `DISCORD_TOKEN` through `.env`, your shell, or Portainer, then run:

```sh
docker compose pull
docker compose up -d
docker compose logs -f --tail=50
```

No published ports are required. The container runs as a non-root user. Setup, building, publishing, and updates: [DOCKER.md](DOCKER.md). Docker Hub description: [DOCKERHUB.md](DOCKERHUB.md).

## Discord commands

Upload an image and send `@sirmagick help` or `@sirmagick EFFECT`. You can also supply a public image URL: `@sirmagick droste https://example.org/image.jpg`.

| Group | Commands |
|---|---|
| Original face effects | `blockface`, `warpface`, `chudthor` |
| New face effects | `fatmagic`, `tinyface`, `bigmouth`, `googly`, `eyeswap` |
| Image effects | `wide` (three times the width), `deepfry` |
| Trippy | `zoom`, `tunnel`, `kaleidoscope`, `swirl`, `rgbghost` |
| Complex coordinates / Euler | `droste`, `complexsquare`, `complexexp`, `logpolar`, `inversion` |
| Anime decals | `sweat`, `sparkle`, `angry` |
| Other | `random`, `help` |

`random` selects one of the available effects per request and names it in the result. If it selects a face effect and no face is detected, that request fails normally. Anime `uwu` and `blush` are still being refined and are not registered as bot commands.

The bot uses an attachment on the command or searches up to 50 earlier channel messages for an image. Outputs from the bot can be processed again. Each new face request detects landmarks again; sufficiently distorted faces may no longer be recognized. All detected faces are processed. GIFs use only their first frame. Direct messages are ignored.

Slash equivalents are registered at startup. Mention commands work independently of whether Discord displays the slash list. Bot replies and help text are currently in German. Discord setup and permissions: [DISCORD.md](DISCORD.md).

## Behavior and limits

One job runs at a time, up to ten additional jobs wait, and each user may have one pending or running job. A failed or timed-out job does not block later jobs. Processing runs in a persistent CPU subprocess; a hard timeout kills it and the next job starts a new one. Restarts discard queued jobs.

Input limits: 25 MiB and 24 million pixels. Ultrawide also checks the resulting pixel count, so repeated widening may eventually reach the limit. Downloads only allow public HTTP(S) targets, including DNS and redirect checks. Temporary job files are removed after processing.

Effects have fixed strengths. `fatmagic` uses approximate torso landmarks rather than a precise person mask, so it can also stretch nearby background. Trippy and Euler effects work without a face or detection models. Complex-coordinate effects reflect samples outside the image and regularize singularities. Anime decals follow facial landmarks and can accumulate on repeated application.

Settings and defaults are documented in [.env.example](.env.example) and [compose.yaml](compose.yaml). Images and tokens are never bundled in the build context: `.dockerignore` allows only the required Python source and build files. A build-time audit rejects image files and `.env` in the application directories.

## Local development

Use Python 3.12. On Windows:

```powershell
python -m venv .venv
python -m pip --python .venv install -r requirements.txt
.venv\Scripts\python.exe -m sirmagick download-models
.venv\Scripts\python.exe -m sirmagick bot
```

All specific bot effects are also available as local CLI commands; `random` is currently bot-only:

```powershell
.venv\Scripts\python.exe -m sirmagick droste path/to/image.jpg --output output-droste
.venv\Scripts\python.exe -m sirmagick tinyface path/to/image.jpg --output output-tinyface
.venv\Scripts\python.exe -m unittest discover -s tests -q
```

Local comparison scripts are in `tools/preview_*.py`. They write original / first pass / second pass comparisons under ignored `examples/` subfolders. Image assets, examples, outputs, `.env`, models, and virtual environments are excluded from Git. No personal photos are needed by the automated tests.

Source: [GitLab](https://gitlab.kurdy.de/kurdy/sirmagick).
