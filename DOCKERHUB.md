# SirMagick

A Discord bot for bizarre image effects. Runs on your CPU; no GPU required. Detection models are included in the image.

**Image:** `kurdy/sirmagick:latest` | **Platform:** Linux/amd64

**Source code and documentation:** [GitHub](https://github.com/kurdy91x/SirMagick)

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

All slash commands use the `sm_` prefix. Type `/sm_` in Discord, then choose an effect such as `/sm_tron`, `/sm_rift`, or `/sm_blockface`; help is `/sm_help`. The table below lists short effect names: add `sm_` for slash commands. Mention commands keep the short names.

Upload an image to a channel and mention the bot:

```text
@sirmagick help
@sirmagick blockface
@sirmagick deepfry https://example.org/image.jpg
```

| Command | Effect |
|---|---|
| `achievement` | Steam-style achievement card; text requires a title and description |
| `alienface` | Long gray alien face with large dark eyes and tiny features |
| `angry` | Adds an anime anger symbol |
| `animerays` | Stretch the supplied anime action rays over the image |
| `bigmouth` | Enlarges the mouth |
| `blackmetalcover` | Monochrome album cover with a branching root logo; text: TITLE subtitle text |
| `blockface` | Shrinks the inner face and stretches the surrounding strip of skin |
| `blush` | Adds textured cheek tint and small anime hatch marks |
| `buythedip` | A collapsing red chart and irrationally optimistic Bitcoin slogans |
| `censorbar` | A black eye bar following each detected head tilt |
| `censorface` | Frosted glass blur over every detected face |
| `chanpost` | Generate a fictional imageboard screenshot with repeated-digit post IDs |
| `chudthor` | Creates a bizarre, more angular facial distortion |
| `combobreaker` | Add a large C-C-C-COMBOBREAKER wordmark |
| `complexexp` | Warps the image using a complex exponential |
| `complexsquare` | Folds image coordinates using a complex square |
| `crt` | Curved retro monitor, scanlines, and color fringes (Retro) |
| `dealwithit` | Pixel sunglasses and a blunt aligned to each detected face |
| `deathmetalcover` | Deep red and charcoal album cover with a dense jagged logo; text: TITLE subtitle text |
| `deepfry` | Adds exaggerated colors, noise, JPEG artifacts, and random stickers |
| `devilhorns` | Glossy curved horns aligned with each head |
| `droste` | Repeats the image in a logarithmic spiral |
| `emboss` | Lit metallic relief (Depth) |
| `extrude` | Colored sidewalls and shadows along image contours (Depth) |
| `eyeswap` | Replaces the nose and mouth with copies of an eye |
| `eyevortex` | Twisting cylindrical streams covered in repeated eyes |
| `fatmagic` | Broaden detected torsos smoothly with mild face widening |
| `firebreath` | Procedural flame jet from each detected mouth |
| `fisheye` | Wide-angle lens bulge (Trippy) |
| `giga` | Exaggerate the jaw width and chin |
| `glitch` | Digital tearing, shifted bands, and RGB errors (Retro) |
| `goblin` | Enlarge the nose and mouth and shrink the eyes |
| `googly` | Enlarges the eyes |
| `halftone` | Comic print dots and reduced colors (Retro) |
| `halo` | A glowing golden halo aligned with each head |
| `help` | Shows the command overview |
| `hellface` | Combine glowing laser eyes and fire breath |
| `hodl` | Orange Bitcoin hype, coins, rocket, and a rising green chart |
| `hornijail` | Put the image behind the window panes of the horny jail meme |
| `inversion` | Inverts the center and outer image through complex coordinates |
| `julia` | Image-colored Julia fractal patterns (Fractal) |
| `kaleidoscope` | Mirrors the image into six sectors |
| `kaliyuga` | Breaking-news bars announcing 426,877 years left in the Kali Yuga |
| `lasereyes` | Glowing red eyes and bright laser beams |
| `letters` | Rebuilds the image from colored letters with varying sizes and density |
| `logpolar` | Unwraps circles into straight bands |
| `longface` | Stretch the face into a long narrow oval |
| `meltface` | Let facial features melt downward |
| `metalcover` | Monochrome album cover with an angular thorn logo; text: TITLE subtitle text |
| `mouthvortex` | Twisting cylindrical streams covered in repeated mouths |
| `newton` | Image-colored Newton fractal basins (Fractal) |
| `nightvision` | Green low-light contrast, grain, and scanlines |
| `numbers` | Rebuilds the image from colored digits with varying sizes and density |
| `prismglow` | Saturated prism reflections, bokeh, warm/cool light leaks, and glow |
| `random` | Selects a random available effect and names it in the result |
| `redeyes` | Bloodshot sclera with fine red veins, preserving the iris |
| `rgbghost` | Shifts color channels apart |
| `rift` | Twisted mirrored shards, neon seams, and a dark dimensional tear |
| `sparkle` | Adds anime sparkle stars |
| `surveillance` | Face tracking locks, tactical status panels, REC, and UTC timestamp |
| `sweat` | Adds an anime sweat drop |
| `swirl` | Twists the image into a spiral |
| `thanos` | Directional disintegration into drifting image-colored dust |
| `thermal` | Simulated heat-camera colors from brightness |
| `tinyface` | Shrinks the eyes, nose, and mouth together |
| `tron` | Sparse landmark-aligned facial light segments and simplified cyan contours |
| `tunnel` | Creates a rotating tunnel of nested image copies |
| `uwu` | Enlarges eyes slightly, shrinks the mouth, and adds soft blush |
| `vortexcolumns` | Twisting cylindrical streams covered in repeated faces |
| `warpface` | Enlarges the head and shrinks facial features |
| `wasted` | Desaturate the scene and add the supplied wasted wordmark |
| `wide` | Stretches the entire image to three times its width |
| `youdied` | Darken the scene and add the supplied YOU DIED wordmark |
| `zoom` | Adds zoom ghost exposures |

Trippy and complex-coordinate effects do not require faces. `random` can select a face effect; if no face is detected, the job fails with the usual error message. Repeated `wide` applications increase the width again, up to the 24-million-pixel output limit. `uwu` adds cute facial proportions and blush; `blush` adds soft cheek tint and anime hatch marks.

Vortex modes use a working canvas capped at 1600 pixels on its longest side and render in small strips to reduce temporary memory use. Results retain the original dimensions and alpha; large images may appear softer.

Without a URL, the bot uses an image attached to your command or the latest image in the channel. Bot-generated images can be processed again. Face effects apply to all detected faces; if no face is detected, the job fails with an error message. GIFs are processed as a single image using their first frame.

Slash commands are registered at startup. If they do not appear in Discord, use mention commands instead. Bot replies, help text, and command descriptions are in English.


`achievement` requires a `text` option: its first word is the title and the remaining words are the description (400 characters maximum). Example: `@sirmagick achievement TouchGrass Finally went outside.` Add an image attachment or an image URL at the end. The output is a 1200x650 card; `chanpost` produces a fictional 1200x820 screenshot with doubles/trips-or-higher post IDs and never connects to an imageboard. `hornijail` places the image behind three perspective-aligned window panes and returns the opaque template dimensions. Other new modes keep the input dimensions and alpha. Random mode skips `achievement` and the three metal-cover modes because they need user text.

The experimental `comic` and `anime` photo filters have been removed; character redraws need a separate generative model. `fatmagic` smoothly widens detected torsos when reliable shoulder/hip points exist; otherwise only the face is changed. `censorface` is a stylized blur and is not a guarantee of anonymization. Face masks and face transformations require a detected face; heavy edits can prevent detection on the next request.

The supplied Anime Rays, YOU DIED, and wasted assets have white JPG backgrounds. White is removed during compositing; the Anime Rays image is stretched to the input aspect ratio.

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

SirMagick's own code is MIT licensed. The image includes `/app/LICENSE`,
`/app/THIRD_PARTY_NOTICES.md`, and `/app/licenses/Apache-2.0.txt`.
Dependencies, models, and operating system packages retain their own licenses.

All Discord slash commands use the `sm_` prefix: `/sm_blockface`, `/sm_halo`, `/sm_random`, `/sm_help`, and every other effect. Type `/sm_` to filter the command list. The tables list effect names; add `sm_` for slash commands. Mention commands retain short names, such as `@sirmagick halo`. After rebuilding and restarting, commands are published globally only. Once global registration succeeds, the bot removes legacy guild-specific copies in joined servers to prevent duplicate entries. If global registration fails, existing guild commands are retained.

### Metal album covers

`metalcover`, `blackmetalcover`, and `deathmetalcover` require text in the form `TITLE subtitle text`. Example: `@sirmagick blackmetalcover SEPULCHER Beneath the Last Sun`. Slash commands have a required `text` option. The first word appears as the title at the top (up to 48 characters); the remaining words appear at the bottom (up to 100 characters). No pipe separator is needed. The three logo styles are angular thorns, branching roots, and dense jagged lettering. Metalcover is dark photographic monochrome, Blackmetalcover is harsh xerox-style black and white, and Deathmetalcover is deep red and charcoal. The three logo fonts are Metal Lord (Metalcover), Dystopian Canticle (Blackmetalcover), and Art Dystopia (Deathmetalcover). They produce opaque 900x900 covers with grain, scratches, and dark edges, using CPU only and no face detection. The input is center-cropped to a square.
