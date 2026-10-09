"""Explicit download of the official MediaPipe models."""

from pathlib import Path
from urllib.request import urlopen
import os
import zipfile

MODEL_URLS = {
    "face_landmarker.task": "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task",
    "pose_landmarker_lite.task": "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task",
}


def download_models(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, url in MODEL_URLS.items():
        target = directory / name
        if target.is_file() and zipfile.is_zipfile(target):
            paths.append(target)
            continue
        temporary = target.with_suffix(".download")
        try:
            with urlopen(url, timeout=60) as response, temporary.open("wb") as output:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 100 * 1024 * 1024:
                        raise ValueError("Model download exceeds 100 MiB.")
                    output.write(chunk)
            if not zipfile.is_zipfile(temporary):
                raise ValueError(f"Invalid model archive: {name}")
            os.replace(temporary, target)
        finally:
            temporary.unlink(missing_ok=True)
        paths.append(target)
    return paths
