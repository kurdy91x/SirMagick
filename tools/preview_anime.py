"""Face-anchored anime decals; private previews stay in examples/anime/."""
import json
import math
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

from preview_modes import comparison, local_scale
from sirmagick.chudthor import OVAL
from sirmagick.detection import Detector
from sirmagick.warpface import EYES, MOUTH

from sirmagick.anime import MODES, apply_effect


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "examples/new-modes/original.png"
    with Image.open(source) as original:
        image = original.convert("RGBA")
    output = root / "examples/anime"
    output.mkdir(parents=True, exist_ok=True)
    overview = Image.new("RGB", (1800, 700*len(MODES)), "#181818")
    with Detector(root / "models") as detector:
        detection = detector.detect(image)
        for index, mode in enumerate(MODES):
            first = apply_effect(image, detection, mode)
            second = apply_effect(first, detector.detect(first), mode, pass_number=2)
            assert image.size == first.size == second.size
            first.save(output / f"{mode}.png")
            second.save(output / f"{mode}-2x.png")
            paired = comparison(image, first, second, mode)
            paired.save(output / f"{mode}-vergleich.jpg", quality=93)
            overview.paste(paired, (0, index*700))
            print("Saved:", mode, flush=True)
    overview.save(output / "alle-anime-vergleich.jpg", quality=93)
    (output / "report.json").write_text(json.dumps({"source": str(source.relative_to(root)),
        "modes": MODES, "passes": 2, "prototype": True, "requires_detection": True,
        "note": "Sweat/angry alternate sides and sparkle shifts on pass two to show stacking."}, indent=2))


if __name__ == "__main__":
    main()
