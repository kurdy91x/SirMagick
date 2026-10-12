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

For slash commands, type `/sm_` and choose an effect, such as `/sm_halo` or `/sm_blockface`. Every slash command uses this prefix, including `/sm_random` and `/sm_help`. The table below lists short effect names; mention commands and local CLI commands use these short names directly.

| Group | Commands |
|---|---|
| Original face effects | `blockface`, `warpface`, `chudthor` |
| New face effects | `fatmagic`, `tinyface`, `bigmouth`, `googly`, `eyeswap` |
| Image effects | `wide` (three times the width), `deepfry` |
| Trippy | `zoom`, `tunnel`, `kaleidoscope`, `swirl`, `rgbghost` |
| Complex coordinates / Euler | `droste`, `complexsquare`, `complexexp`, `logpolar`, `inversion` |
| Anime decals | `uwu`, `blush`, `sweat`, `sparkle`, `angry` |
| Other | `random`, `help` |
| Retro | `glitch`, `crt`, `halftone` |
| Fractal | `julia`, `newton` |
| Depth | `extrude`, `emboss` |
| Typography | `numbers`, `letters` |
| Cinematic / memes | `thermal`, `nightvision`, `thanos`, `dealwithit` |
| Neon | `tron` |
| Dimensional | `rift` |
| Face fantasy | `halo`, `devilhorns`, `vortexcolumns` |
| Feature vortex | `eyevortex`, `mouthvortex` |
| Lens | `fisheye` |
| Face transformers | `alienface`, `longface`, `goblin`, `giga`, `meltface`, `fatmagic` |
| Face masks | `censorface`, `censorbar`, `redeyes`, `lasereyes`, `firebreath`, `hellface` |
| Surveillance HUD | `surveillance` |
| Meme layouts | `combobreaker`, `youdied`, `wasted`, `animerays`, `achievement`, `chanpost`, `hornijail` |
| Meme feeds | `hodl`, `buythedip`, `kaliyuga` |
| Metal album covers | `metalcover`, `blackmetalcover`, `deathmetalcover` |
| Photo styles | `prismglow` |

The three Vortex modes render in 96-row strips on a working canvas capped at 1600 pixels on its longest side, then restore the original dimensions and alpha. This bounds their temporary rendering memory; large outputs may be softer than full-resolution rendering.

`rift` shatters the image into twisted, mirrored fragments with cyan/magenta seams and a dark central tear. It needs no detection, runs on CPU, and preserves output dimensions and the original alpha mask. Preview four private comparisons with `python tools/preview_cinematic.py --modes rift`.

`tron` combines sparse, smooth landmark-aligned facial light segments with simplified contours on hair and clothing. It runs on CPU and preserves output dimensions and alpha. The bot and CLI use the existing detector; images without faces still work with simplified image contours. Preview with `python tools/preview_cinematic.py --modes tron`; private comparisons stay in `examples/cinematic/`.

`thermal` simulates heat-camera colors from brightness (it does not measure temperature). `nightvision` adds green low-light contrast, grain, and scanlines. `thanos` disintegrates the right side into drifting image-colored particles. `dealwithit` places the supplied pixel shades and blunt on every detected face; it requires face detection. The allowlisted overlay assets are explicitly packaged in the wheel and Docker image; private test photos remain excluded. Generate private three-column comparisons with `python tools/preview_cinematic.py` under `examples/cinematic/`.

`numbers` and `letters` render colored digits or uppercase letters on a dark background, varying glyph size and density with image details and brightness. They work without faces and use Pillow's bundled scalable font. Output dimensions and the original alpha mask are preserved; glyph rendering is bounded to a 1600-pixel working canvas. Run `python tools/preview_typography.py` for four private input comparisons and full-size first-pass PNGs together under ignored `examples/typography/`.

`eyevortex` tiles both eyes from every detected face across twisting cylindrical streams; `mouthvortex` uses their mouths. Both keep the same fixed vortex geometry as `vortexcolumns`. Generate private comparisons together under `examples/vortexcolumns/` with `python tools/preview_face_fantasy.py --modes eyevortex mouthvortex`. Second passes may fail if full faces are no longer detectable.


`random` selects one of the available effects per request and names it in the result. If it selects a face effect and no face is detected, that request fails normally. `uwu` adds cute facial proportions and blush; `blush` adds cheek tint and anime hatch marks while retaining the original facial texture.

The bot uses an attachment on the command or searches up to 50 earlier channel messages for an image. Outputs from the bot can be processed again. Each new face request detects landmarks again; sufficiently distorted faces may no longer be recognized. All detected faces are processed. GIFs use only their first frame. Direct messages are ignored.

Slash equivalents are registered at startup. Mention commands work independently of whether Discord displays the slash list. Bot replies, help text, and command descriptions are in English. Discord setup and permissions: [DISCORD.md](DISCORD.md).

## Behavior and limits

One job runs at a time, up to ten additional jobs wait, and each user may have one pending or running job. A failed or timed-out job does not block later jobs. Processing runs in a persistent CPU subprocess; a hard timeout kills it and the next job starts a new one. Restarts discard queued jobs.

Input limits: 25 MiB and 24 million pixels. Ultrawide also checks the resulting pixel count, so repeated widening may eventually reach the limit. Downloads only allow public HTTP(S) targets, including DNS and redirect checks. Temporary job files are removed after processing.

Effects have fixed strengths. `fatmagic` uses approximate torso landmarks rather than a precise person mask, so it can also stretch nearby background. Trippy and Euler effects work without a face or detection models. Complex-coordinate effects reflect samples outside the image and regularize singularities. Anime decals follow facial landmarks and can accumulate on repeated application.

Settings and defaults are documented in [.env.example](.env.example) and [compose.yaml](compose.yaml). Private images and tokens are never bundled in the build context: `.dockerignore` allows only the required source, build/license files, and the six explicit effect overlays. A build-time audit rejects all other image files and `.env` in the application directories.

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

Local comparison scripts are in `tools/preview_*.py`. They write original / first pass / second pass comparisons under ignored `examples/` subfolders. Private image assets, examples, outputs, `.env`, models, and virtual environments are excluded from Git. Only the six allowlisted effect overlays are tracked and packaged. No personal photos are needed by the automated tests.

To compare the rebuilt anime effects across your private test images:

```powershell
.venv\Scripts\python.exe tools/preview_anime.py --source examples/testimages --output examples/anime/multi --modes uwu blush
```

Each detected image gets separate three-column comparisons. `batch-report.json` records missing detections and second-pass failures; these do not stop the batch.

Source: [GitHub](https://github.com/kurdy91x/SirMagick).

SirMagick's own code is licensed under the [MIT License](LICENSE).
Dependencies and models retain their own licenses; see [third-party notices](THIRD_PARTY_NOTICES.md).

Generate Retro and fisheye comparisons with `python tools/preview_retro.py`. Private three-column comparisons are saved directly under `examples/retro-new/`. To check only the stronger CRT effect on four varied images, use `python tools/preview_retro.py --modes crt --limit 4`.

Fractal effects work without faces. Julia and Newton use image-colored complex iterations. Iteration fields are limited to 800 pixels on the longest side, while output dimensions remain unchanged. Generate private comparisons on four varied inputs with `python tools/preview_fractal.py`; all results are saved together under `examples/fractal/`.

Depth effects work without faces or extra models. `extrude` builds colored sidewalls from contours; `emboss` lights a brightness-based metallic relief. They preserve output dimensions and alpha, without reconstructing scene geometry. Private comparisons: `python tools/preview_depth.py`, saved together under ignored `examples/depth/`.

Face fantasy effects require detected faces. `halo` adds a glowing golden ring, `devilhorns` adds glossy curved horns; both follow head size and eye-line rotation. `vortexcolumns` tiles all detected faces onto twisting cylindrical streams with surface shading. Repeated processing detects faces again and can fail if the result is too distorted. Run `python tools/preview_face_fantasy.py` for private comparisons under `examples/headgear/` and `examples/vortexcolumns/`.

All Discord slash commands use the `sm_` prefix: `/sm_blockface`, `/sm_halo`, `/sm_random`, `/sm_help`, and every other effect. Type `/sm_` to filter the command list. The tables list effect names; add `sm_` for slash commands. Mention commands retain short names, such as `@sirmagick halo`. After rebuilding and restarting, commands are published globally only. Once global registration succeeds, the bot removes legacy guild-specific copies in joined servers to prevent duplicate entries. If global registration fails, existing guild commands are retained.

## New effect review batch

Run `python tools/preview_new_effects.py` to generate 27 variants on four inputs under ignored `examples/new-effects/`. Open its `index.html` to filter the flat gallery by effect. Comparisons show original / first pass / second pass, with first-pass PNGs and `report.json` beside them. The input selection includes close portraits and detected torsos. A failed second face detection is displayed rather than bypassed. Use `--modes fatmagic redeyes` to regenerate only selected variants.

Achievement text is required: `/sm_achievement text:TouchGrass Finally went outside.` or `@sirmagick achievement TouchGrass Finally went outside.` The first word becomes the title, the rest the description; text is limited to 400 characters. Mention commands allow an image URL after the description. Locally: `python -m sirmagick achievement INPUT --text "TouchGrass Finally went outside." --output output-achievement`. The worker receives the same text through the shared queue. Achievement produces a 1200x650 Steam-style card; Chanpost produces a fictional 1200x820 imageboard screenshot with random comments and repeated-digit IDs, entirely offline. Random mode excludes Achievement because it requires text.

Hornijail uses the supplied 932x810 meme template and inserts the image behind its three window panes. The other new effects preserve dimensions and alpha, using working canvases bounded to 1400 pixels (900 for Prismglow). They may soften large inputs. The experimental Comic and Anime photo filters have been removed. Generative character redraws would require a separate model. Fatmagic smoothly widens reliable torsos and mildly broadens faces; images without visible shoulder/hip landmarks receive face-only processing. Goblin enlarges the temple areas as a rough ear approximation; ears are not separately detected. The censorship modes are visual effects, not guaranteed anonymization. Red eyes tint the brighter sclera and mask the detected iris; small or closed eyes have limited detail. Firebreath and laser direction are estimated from 2D face points.

Supplied JPG wordmarks and action rays are composited with white removed; Anime Rays is stretched to the input aspect ratio. Only exact filenames in `sirmagick/asset_manifest.py` may be packaged. Private input images and comparison renders remain excluded from Git and Docker.

Prismglow uses float32 buffers, a reduced-resolution bloom pass, and local bokeh patches on a 900-pixel working canvas to limit CPU and memory use. Worker logs identify decode, detection, render, and encode stages when diagnosing processing timeouts.

## Metal album covers

Use `/sm_metalcover text:SEPULCHER Beneath the Last Sun` or `@sirmagick metalcover SEPULCHER Beneath the Last Sun`. The first word is the title at the top (up to 48 characters); the remaining words appear at the bottom (up to 100 characters). No pipe separator is needed. A trailing image URL is supported for mentions. CLI: `python -m sirmagick metalcover INPUT --text "SEPULCHER Beneath the Last Sun" --output output-metalcover`.

`metalcover` draws angular thorns, `blackmetalcover` draws branching roots, and `deathmetalcover` draws compact jagged extensions. The three logo fonts are Metal Lord (Metalcover), Dystopian Canticle (Blackmetalcover), and Art Dystopia (Deathmetalcover). Metalcover keeps a dark photographic monochrome look; Blackmetalcover uses harsh xerox-style black and white; Deathmetalcover uses deep red and charcoal. Covers use square center crops, grain, vignette, and scratches. They produce opaque 900x900 covers on CPU without detection or additional models. Long text is fitted to the available space. Random mode excludes these commands because they require text. Private previews: `python tools/preview_new_effects.py --modes metalcover blackmetalcover deathmetalcover`.

Image overlays live in `sirmagick/assets/img/`; reviewed font binaries and their license notices live in `sirmagick/assets/font/`. Original font ZIP archives are excluded from Git and Docker. Art Dystopia and Metal Lord are listed as Public Domain by their source pages; Dystopian Canticle uses SIL OFL 1.1. Per-font sources and license information are documented in `THIRD_PARTY_NOTICES.md`; the original SIL OFL license is bundled with Dystopian Canticle.
