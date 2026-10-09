# SirMagick

A Discord bot for bizarre image effects. Runs on your CPU; no GPU required. Detection models are included in the image.

**Image:** `kurdy/sirmagick:latest` | **Platform:** Linux/amd64

## Quick start

Create a bot in the Discord Developer Portal, enable **Message Content Intent**, and invite it to your server. Required channel permissions: **View Channels**, **Read Message History**, **Send Messages**, and **Attach Files**. For threads, also enable **Send Messages in Threads**.

Save this as `compose.yaml`:

```yaml
services:
  sirmagick:
    image: kurdy/sirmagick:latest
    init: true
    restart: unless-stopped
    environment:
      DISCORD_TOKEN: "${DISCORD_TOKEN:?Please set DISCORD_TOKEN}"
      # Optional: comma-separated lists of allowed server/channel IDs.
      ALLOWED_GUILD_IDS: "${ALLOWED_GUILD_IDS:-}"
      ALLOWED_CHANNEL_IDS: "${ALLOWED_CHANNEL_IDS:-}"
    read_only: true
    tmpfs:
      - /tmp:rw,nosuid,nodev,size=512m,mode=1777
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    cpus: "2.0"
    mem_limit: 2g
    pids_limit: 256
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

Create a `.env` file in the same directory:

```dotenv
DISCORD_TOKEN=YOUR_DISCORD_BOT_TOKEN
```

Alternatively, set `DISCORD_TOKEN` through your shell or Portainer's stack environment variables. Use your **Discord bot token**, not the client secret or a Docker Hub access token.

```sh
docker compose pull
docker compose up -d
docker compose logs -f --tail=50
```

No published ports or additional volumes are needed. The container runs as a non-root user. Allow outbound access to Discord, DNS, and image download sources.

## Usage

Upload an image to a channel and mention the bot:

```text
@sirmagick help
@sirmagick blockface
@sirmagick deepfry https://example.org/image.jpg
```

| Command | Effect |
|---|---|
| `blockface` | Shrinks the inner face and stretches the surrounding strip of skin |
| `warpface` | Enlarges the head and shrinks facial features |
| `chudthor` | Creates a bizarre, more angular facial distortion |
| `deepfry` | Adds exaggerated colors, noise, JPEG artifacts, and random stickers |
| `help` | Shows the command overview |
| `fatmagic` | Widens the face and detected torso (approximate body shape) |
| `tinyface` | Shrinks the eyes, nose, and mouth together |
| `bigmouth` | Enlarges the mouth |
| `googly` | Enlarges the eyes |
| `eyeswap` | Replaces the nose and mouth with copies of an eye |
| `wide` | Stretches the entire image to three times its width |
| `zoom` | Adds zoom ghost exposures |
| `tunnel` | Creates a rotating tunnel of nested image copies |
| `kaleidoscope` | Mirrors the image into six sectors |
| `swirl` | Twists the image into a spiral |
| `rgbghost` | Shifts color channels apart |
| `droste` | Repeats the image in a logarithmic spiral |
| `complexsquare` | Folds image coordinates using a complex square |
| `complexexp` | Warps the image using a complex exponential |
| `logpolar` | Unwraps circles into straight bands |
| `inversion` | Inverts the center and outer image through complex coordinates |
| `sweat` | Adds an anime sweat drop |
| `sparkle` | Adds anime sparkle stars |
| `angry` | Adds an anime anger symbol |
| `random` | Selects a random available effect and names it in the result |

Trippy and complex-coordinate effects do not require faces. `random` can select a face effect; if no face is detected, the job fails with the usual error message. Repeated `wide` applications increase the width again, up to the 24-million-pixel output limit. `uwu` and `blush` are still being refined and are not enabled as bot commands.

Without a URL, the bot uses an image attached to your command or the latest image in the channel. Bot-generated images can be processed again. Face effects apply to all detected faces; if no face is detected, the job fails with an error message. GIFs are processed as a single image using their first frame.

Slash commands are registered at startup. If they do not appear in Discord, use mention commands instead. Bot replies and help text are currently in German.

## Optional settings

Add these variables under `environment` in your Compose file:

| Variable | Default | Description |
|---|---|---|
| `ALLOWED_GUILD_IDS` | empty | Allowed server IDs; empty allows all accessible servers |
| `ALLOWED_CHANNEL_IDS` | empty | Allowed channel IDs; empty allows all accessible channels |
| `QUEUE_SIZE` | `10` | Maximum number of waiting jobs |
| `USER_COOLDOWN_SECONDS` | `5` | Minimum interval between jobs from the same user |
| `HISTORY_LIMIT` | `50` | Number of previous messages searched for an image |
| `PROCESS_TIMEOUT_SECONDS` | `60` | Processing time limit per image, in seconds |
| `MAX_DOWNLOAD_BYTES` | `26214400` | Download limit: 25 MiB |
| `MAX_OUTPUT_BYTES` | `8388608` | Upload limit: 8 MiB, also subject to Discord's server limit |

The bot processes one job at a time and allows one pending or running job per user. Failed jobs do not block the queue. Restarting the container discards queued jobs. Direct messages are ignored.

## Updates

```sh
docker compose pull
docker compose up -d
```

Source code and detailed setup instructions: [GitLab - SirMagick](https://gitlab.kurdy.de/kurdy/sirmagick).
