"""Private three-column fractal comparisons, together in examples/fractal/."""
import json
from pathlib import Path
from time import perf_counter

from PIL import Image

from preview_modes import comparison
from sirmagick.effects import apply_effect
from sirmagick.images import image_paths, load_image
from sirmagick.fractal import MODES


def main():
    root = Path(__file__).resolve().parents[1]
    paths = image_paths(root / "examples/testimages")
    count = min(4, len(paths))
    paths = [paths[i*(len(paths)-1)//max(1, count-1)] for i in range(count)]
    output = root / "examples/fractal"
    output.mkdir(parents=True, exist_ok=True)
    report = []
    for path in paths:
        image = load_image(path)
        image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
        for mode in MODES:
            start = perf_counter()
            first = apply_effect(image, None, mode)
            second = apply_effect(first, None, mode)
            comparison(image, first, second, mode).save(output / f"{mode}--{path.name}--comparison.jpg", quality=93)
            report.append({"source": path.name, "mode": mode, "two_pass_seconds": round(perf_counter()-start, 3)})
            print(path.name, mode, report[-1]["two_pass_seconds"], flush=True)
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
