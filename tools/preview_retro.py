"""Keep all new-effect comparisons together in one private folder."""
import json
import argparse
from pathlib import Path

from PIL import Image

from preview_modes import comparison
from contextlib import nullcontext
from sirmagick.images import image_paths, load_image
from sirmagick.effects import apply_effect
from sirmagick.retro import MODES


def main():
    root = Path(__file__).resolve().parents[1]
    source, output = root / "examples/testimages", root / "examples/retro-new"
    output.mkdir(parents=True, exist_ok=True)
    parser = argparse.ArgumentParser(description="Generate private retro comparisons")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=MODES)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    paths = image_paths(source)
    if args.limit is not None:
        if args.limit < 1:
            parser.error("--limit must be positive")
        count = min(args.limit, len(paths))
        paths = [paths[i*(len(paths)-1)//max(1, count-1)] for i in range(count)]
    reports = []
    with nullcontext():
        for path in paths:
            image = load_image(path)
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            for mode in args.modes:
                first = second = None
                error = None
                try:
                    first = apply_effect(image, None, mode)
                    second = apply_effect(first, None, mode)
                except ValueError as exc:
                    error = str(exc)
                target = output / f"{mode}--{path.name}--comparison.jpg"
                comparison(image, first, second, mode, error).save(target, quality=93)
                reports.append({"source": path.name, "effect": mode, "first_pass": first is not None,
                                "second_pass": second is not None, "error": error})
            print("Compared:", path.name, flush=True)
    report_path = output / "report.json"
    previous = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else []
    previous = [entry for entry in previous if entry["effect"] in MODES and entry["effect"] not in args.modes]
    report_path.write_text(json.dumps(previous+reports, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
