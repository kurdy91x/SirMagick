FROM python:3.12-slim-bookworm

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
# Copy Python source files only, even if extra assets appear in this directory.
COPY sirmagick/*.py ./sirmagick/
RUN python -m pip install . \
    && python -m sirmagick download-models --models /app/models \
    && python -c "import cv2, discord, mediapipe; from sirmagick.detection import Detector; detector = Detector(__import__('pathlib').Path('/app/models')); detector.close()"

# Check both the copied source and the installed package before publishing.
RUN python -c "from pathlib import Path; from importlib.metadata import distribution; roots = [Path('/app'), Path(distribution('sir-magick').locate_file('sirmagick'))]; forbidden = [str(p) for root in roots for p in root.rglob('*') if p.is_file() and (p.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tif', '.tiff', '.avif', '.heic'} or p.name == '.env')]; assert not forbidden, 'Unexpected images or secrets in application files: ' + repr(forbidden); print('Image audit passed: no image files or .env in application files')"

USER 10001:10001
CMD ["python", "-m", "sirmagick", "bot"]
