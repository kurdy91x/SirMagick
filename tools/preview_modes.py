"""Local prototypes only: all input/output images stay under ignored examples/."""
import json
import math
import secrets
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageOps
from sirmagick.chudthor import OVAL, bilinear_rgba, radial_source
from sirmagick.detection import Detector
from sirmagick.images import image_paths, load_image
from sirmagick.warpface import EYES, MOUTH, NOSE

from sirmagick.face_modes import MODES, apply_mode, local_scale


def comparison(image, edited, repeated, title, error=None):
    canvas = Image.new("RGB", (1800, 700), "#181818")
    draw = ImageDraw.Draw(canvas)
    draw.text((20, 14), "Original", fill="white")
    draw.text((620, 14), title + " - 1x", fill="white")
    draw.text((1220, 14), title + " - 2x", fill="white")
    for x, source in ((0, image), (600, edited), (1200, repeated)):
        if source is None:
            draw.text((x+25, 320), error or "Second pass failed", fill="white")
            continue
        source = ImageOps.contain(source.convert("RGB"), (580, 640), Image.Resampling.LANCZOS)
        canvas.paste(source, (x+(600-source.width)//2, 45+(640-source.height)//2))
    return canvas


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "examples/testimages"
    output = root / "examples/new-modes"
    output.mkdir(parents=True, exist_ok=True)
    candidates = []
    with Detector(root / "models") as detector:
        for path in image_paths(source):
            image = load_image(path)
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            detection = detector.detect(image)
            print(path.name, "faces", len(detection.faces), "bodies", len(detection.poses), flush=True)
            if detection.faces:
                face = detection.faces[0]
                score = abs(face[454].x-face[234].x)/image.width
                if len(detection.faces) == 1:
                    score += .3
                if any(all(pose[i].visibility > .5 for i in (11, 12, 23, 24)) for pose in detection.poses):
                    score += .3
                candidates.append((score, path, image, detection))
        if not candidates:
            raise ValueError("No suitable face found")
        _, path, image, detection = max(candidates, key=lambda entry: entry[0])
        print("Selected:", path.name, flush=True)
        image.save(output / "original.png")
        modes = (*MODES, "random")
        random_choice = secrets.choice(MODES)
        overview = Image.new("RGB", (1800, 700*len(modes)), "white")
        repeat_report = {}
        for index, mode in enumerate(modes):
            chosen = random_choice if mode == "random" else mode
            edited = apply_mode(image, detection, chosen)
            edited.save(output / (mode + ".png"))
            repeated = None
            error = None
            repeat_path = output / (mode + "-2x.png")
            try:
                # Redetect on the edited image just as a new bot request would.
                second_detection = detector.detect(edited) if chosen != "wide" else None
                repeated = apply_mode(edited, second_detection, chosen)
                repeated.save(repeat_path)
                repeat_report[mode] = {"status": "ok", "effect": chosen}
            except ValueError as exc:
                repeat_path.unlink(missing_ok=True)
                error = "No face detected after first pass"
                repeat_report[mode] = {"status": "error", "error": str(exc), "effect": chosen}
            paired = comparison(image, edited, repeated,
                                mode if mode != "random" else f"random -> {chosen}", error)
            paired.save(output / (mode + "-vergleich.jpg"), quality=92)
            overview.paste(paired, (0, 700*index))
            print("Saved:", mode, flush=True)
        overview.save(output / "alle-modi-vergleich.jpg", quality=92)
        (output / "report.json").write_text(json.dumps({"source": path.name, "modes": modes,
            "random_choice": random_choice,
            "second_pass": repeat_report,
            "prototype": True, "faces": len(detection.faces), "poses": len(detection.poses),
            "note": "Fatmagic uses approximate torso landmarks, not a person mask. Wide triples image width without cropping."}, indent=2))


if __name__ == "__main__":
    main()
