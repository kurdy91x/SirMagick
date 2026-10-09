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
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 magick \
    && useradd --uid 10001 --gid magick --no-create-home --home-dir /tmp magick

COPY requirements.txt pyproject.toml ./
COPY sirmagick ./sirmagick
RUN python -m pip install . \
    && python -m sirmagick download-models --models /app/models \
    && python -c "import cv2, discord, mediapipe; from sirmagick.detection import Detector; detector = Detector(__import__('pathlib').Path('/app/models')); detector.close()"

USER 10001:10001
CMD ["python", "-m", "sirmagick", "bot"]
