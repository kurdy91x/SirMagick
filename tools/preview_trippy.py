"""CPU-only trippy prototypes; all image artifacts remain under examples/."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from preview_modes import comparison

from sirmagick.trippy import MODES, apply_effect


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "examples/new-modes/original.png"
    image = Image.open(source).convert("RGBA")
    image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    output = root / "examples/trippy"
    output.mkdir(parents=True, exist_ok=True)
    overview = Image.new("RGB", (1800, 700*len(MODES)), "#181818")
    for index, mode in enumerate(MODES):
        first = apply_effect(image, mode)
        second = apply_effect(first, mode)
        first.save(output / f"{mode}.png")
        second.save(output / f"{mode}-2x.png")
        paired = comparison(image, first, second, mode)
        paired.save(output / f"{mode}-comparison.jpg", quality=93)
        overview.paste(paired, (0, index*700))
        assert image.size == first.size == second.size
        print("Saved:", mode, flush=True)
    overview.save(output / "all-trippy-comparison.jpg", quality=93)
    (output / "report.json").write_text(json.dumps({"source": str(source.relative_to(root)),
        "modes": MODES, "passes": 2, "requires_detection": False, "prototype": True}, indent=2))


if __name__ == "__main__":
    main()
