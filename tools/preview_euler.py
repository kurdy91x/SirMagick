"""Complex-coordinate image prototypes, with local-only comparison artifacts."""
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from preview_modes import comparison

from sirmagick.euler import MODES, coordinate_map, apply_effect


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "examples/new-modes/original.png"
    with Image.open(source) as original:
        image = original.convert("RGBA")
    image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    output = root / "examples/euler"
    output.mkdir(parents=True, exist_ok=True)
    overview = Image.new("RGB", (1800, 700*len(MODES)), "#181818")
    for index, mode in enumerate(MODES):
        first = apply_effect(image, mode)
        second = apply_effect(first, mode)
        assert first.size == second.size == image.size
        first.save(output / f"{mode}.png")
        second.save(output / f"{mode}-2x.png")
        paired = comparison(image, first, second, mode)
        paired.save(output / f"{mode}-vergleich.jpg", quality=93)
        overview.paste(paired, (0, index*700))
        print("Saved:", mode, flush=True)
    overview.save(output / "alle-euler-vergleich.jpg", quality=93)
    (output / "report.json").write_text(json.dumps({"source": str(source.relative_to(root)),
        "modes": MODES, "passes": 2, "prototype": True, "requires_detection": False,
        "boundary": "reflected", "singularities": "regularized"}, indent=2))


if __name__ == "__main__":
    main()
