# Third-party licenses

The MIT license in `LICENSE` covers SirMagick's own code. It does not relicense
third-party software, model files, or the container's operating system.

## Direct Python dependencies

| Component | License | Upstream |
| --- | --- | --- |
| MediaPipe | Apache-2.0 | https://github.com/google-ai-edge/mediapipe |
| Pillow | MIT-CMU (HPND variant), plus bundled library licenses | https://github.com/python-pillow/Pillow |
| NumPy | BSD-3-Clause, plus bundled library licenses | https://github.com/numpy/numpy |
| opencv-contrib-python | Packaging: MIT; OpenCV: Apache-2.0; bundled components have additional licenses | https://github.com/opencv/opencv-python |
| discord.py | MIT | https://github.com/Rapptz/discord.py |
| aiohttp | Apache-2.0 AND MIT | https://github.com/aio-libs/aiohttp |
| python-dotenv | BSD-3-Clause | https://github.com/theskumar/python-dotenv |

Installed distributions retain their upstream license and notice files in
Python's `site-packages` directory, usually under `*.dist-info/licenses`.
OpenCV also supplies `cv2/LICENSE.txt` and `cv2/LICENSE-3RD-PARTY.txt`.
Dependency versions and bundled native libraries vary with the platform and build.
Consult the installed notices for the exact image being redistributed.

OpenCV wheels can include FFmpeg (LGPL-2.1) and, on Linux, Qt (LGPL-3.0).
Their redistribution requirements apply independently of SirMagick's MIT license;
the MIT label is not a license declaration for every component in the image.
Upstream packaging and third-party notices:
https://github.com/opencv/opencv-python#licensing

## MediaPipe models

The build downloads these Google MediaPipe bundles:

- Face Landmarker, float16, version 1:
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task
- Pose Landmarker Lite, float16, version 1:
  https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task

Google's Face Mesh V2 and BlazePose GHUM model cards specify Apache License 2.0:

- https://storage.googleapis.com/mediapipe-assets/Model%20Card%20MediaPipe%20Face%20Mesh%20V2.pdf
- https://storage.googleapis.com/mediapipe-assets/Model%20Card%20BlazePose%20GHUM%203D.pdf

A copy of Apache License 2.0 is included at `licenses/Apache-2.0.txt`.
The model files are downloaded unmodified. These model cards describe their
respective model families; they are not a complete inventory of every component
inside a `.task` bundle.

## Container base and transitive dependencies

Python and Debian packages retain their own licenses. Debian copyright files are
available under `/usr/share/doc/*/copyright`; the Python installation includes
its own license. Python transitive dependencies and bundled native libraries
retain their original terms and notices. This document is an overview, not a
complete license audit of a particular published image.

## Supplied meme overlays

`sirmagick/assets/img/anime.rays.jpg`, `wasted.gta.jpg`, `youdied.souls.jpg`, `horni.jail.jpg`, and `cig.leftside.jpg` are maintainer-supplied reference graphics. The game wordmarks refer to their respective third-party games; the MIT license on application code does not grant rights to third-party artwork or trademarks. Original sources and usage rights for these supplied graphics have not been independently verified. `chanpost` and `achievement` use code-drawn layouts, not remote services or screenshots shipped as templates.

## Bundled font

Dystopian Canticle by Scapholene is supplied unmodified in `sirmagick/assets/font/Dystopian-Canticle-Regular.otf` under SIL Open Font License 1.1. Its original copyright and license text is bundled alongside it in `license_Dystopian-Canticle.txt`. Rendered lettering can be distressed or decorated; the font binary is not modified. Art Dystopia (https://www.1001fonts.com/art-dystopia-font.html) and Metal Lord (https://www.1001fonts.com/metal-lord-font.html) are identified as Public Domain by their respective source pages. The linked terms (https://www.1001fonts.com/licenses/public-domain.html) allow use, modification, and redistribution. Original font ZIP archives are not packaged or tracked.
