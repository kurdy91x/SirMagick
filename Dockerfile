FROM python:3.12-slim-bookworm
LABEL org.opencontainers.image.licenses="MIT" \
    org.opencontainers.image.source="https://gitlab.kurdy.de/kurdy/sirmagick"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp \
    MPLCONFIGDIR=/tmp/matplotlib \
    MODEL_DIR=/app/models \
    WORK_DIR=/tmp/sirmagick/jobs

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libegl1 libgles2 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 magick \
    && useradd --uid 10001 --gid magick --no-create-home --home-dir /tmp magick

COPY requirements.txt pyproject.toml ./
COPY LICENSE THIRD_PARTY_NOTICES.md ./
COPY licenses/Apache-2.0.txt ./licenses/Apache-2.0.txt
# Copy source and exactly the two public effect overlays; never private previews.
COPY sirmagick/*.py ./sirmagick/
COPY sirmagick/assets/shades.png sirmagick/assets/blunt.png ./sirmagick/assets/
RUN python -m pip install . \
    && python -c "import shutil; shutil.rmtree('/app/build', ignore_errors=True)" \
    && python -m sirmagick download-models --models /app/models \
    && python -c "import cv2, discord, mediapipe; from sirmagick.detection import Detector; detector = Detector(__import__('pathlib').Path('/app/models')); detector.close()"

# Check both the copied source and the installed package before publishing.
RUN python -c "from pathlib import Path; from importlib.metadata import distribution; roots = [Path('/app'), Path(distribution('sir-magick').locate_file('sirmagick'))]; allowed = {Path('/app/sirmagick/assets') / name for name in ('shades.png', 'blunt.png')} | {roots[1] / 'assets' / name for name in ('shades.png', 'blunt.png')}; forbidden = [str(p) for root in roots for p in root.rglob('*') if p.is_file() and (p.name == '.env' or (p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff', '.avif', '.heic'} and p not in allowed))]; assert not forbidden, 'Unexpected images or secrets in application files: ' + repr(forbidden); assert all(p.is_file() for p in allowed), 'Missing effect overlay assets'; print('Image audit passed: only the two explicit effect overlays are allowed; no .env')"

USER 10001:10001
CMD ["python", "-m", "sirmagick", "bot"]
