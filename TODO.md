# SirMagick project status

The initial functional version is complete. New work is driven by concrete bugs or feature requests.

## Completed

- [x] Python 3.12 with CPU-only processing and reusable MediaPipe face/pose models.
- [x] Prefix every slash command with sm_, including help/random and future catalog entries; replace legacy names during sync. Mention names stay short.
- [x] Retro effects glitch, CRT, halftone; fisheye lens; mirrorface rejected and removed.
- [x] Fractal category with julia and newton; private comparisons on four inputs.
- [x] Depth effects extrude and emboss; anaglyph removed in favor of existing rgbghost.
- [x] Head-aligned golden halos and glossy devil horns; face-textured vortex columns.
- [x] Eye and mouth vortex variants using features from every detected face; sm_ slash prefix inherited automatically.
- [x] Typography modes numbers and letters; bundled font, adaptive glyph sizes, and private comparisons on four inputs.
- [x] Thermal, night vision, Thanos disintegration, and face-aligned shades/blunt with direction-aware mirroring.
- [x] Landmark-aligned Tron lighting and dimensional Rift shards; Outrun rejected and removed.
- [x] Process all detected faces; reject requests lacking required detections.
- [x] Validate image formats, first-frame GIF handling, download and pixel limits.
- [x] Fixed effect strengths; previous bot results can be processed again.
- [x] Original effects: blockface, warpface, chudthor, deepfry.
- [x] Face effects, ultrawide, Trippy, Euler, anime decals, and random mode.
- [x] Rebuild uwu and blush using original facial texture, local scaling, and cheek tint.
- [x] Share the effect catalog across CLI, bot, and worker.
- [x] Mention and slash commands, image attachments, public URLs, channel history, and help.
- [x] Bounded queue, cooldown, one pending job per user, and hard worker timeout.
- [x] Continue after failed jobs; clean temporary files; validate DNS and redirects.
- [x] Global and guild slash registration, confirmed working by the maintainer.
- [x] Docker build and running bot confirmed by the maintainer for an earlier version.
- [x] Compose token parameter, non-root operation, resource limits, and log rotation.
- [x] Exclude private images and tokens from Git and Docker; audit application build files.
- [x] Keep private original / first pass / second pass comparisons under ignored examples/.
- [x] MIT license for project code and third-party notices included in future image builds.
- [x] English documentation, bot responses, command descriptions, CLI messages, and logs.

## Deferred or superseded

- Old blockface mesh/collage variants: replaced by the accepted inner-face scaling effect.
- Minecraft-style body transformation: not implemented; fatmagic widens the face and upper body.
- More precise person masks and improved crowded-group detection: possible future work.
- Strongly distorted faces may no longer be detected on a later request; failure remains valid behavior.
- Persistent queue and automatic hang watchdog: optional future features.

## Verification limits

The maintainer confirmed Docker operation and working slash commands. A complete server-side run of all newer modes, load/memory tests, failure recovery, and restart checks is not fully documented. Docker Hub uploads and removal of older images containing private photos are handled by the maintainer and have not been independently confirmed here. The current development machine has no Docker installation.

These notes describe verification coverage, rather than pending implementation requests. New uwu/blush comparisons are available locally for visual review.

Latest local checks: 58 automated tests passed, including prefixed slash registration, shared queue behavior, and the newer effect families. Live Discord confirmation of the latest prefixed commands still requires rebuilding and restarting the deployed bot.

Private comparisons remain outside Git and Docker under examples/: anime/multi/, retro-new/, fractal/, depth/, headgear/, and vortexcolumns/. Each comparison shows original / first pass / second pass. Missing face detections on later passes are reported rather than bypassed. Mirrorface, Orbitlines, and Anaglyph were rejected or redundant and removed from the active catalog and previews.

Historical ideas: functionality.txt. Current usage and effect list: README.md.
