"""Private comparisons of head ornaments and face-textured vortex columns."""
import json
import argparse
from pathlib import Path
from time import perf_counter

from PIL import Image

from preview_modes import comparison
from sirmagick.detection import Detector
from sirmagick.effects import apply_effect
from sirmagick.images import load_image


def main():
    root = Path(__file__).resolve().parents[1]
    source = root / "examples/testimages"
    parser = argparse.ArgumentParser(description="Generate private face fantasy comparisons")
    parser.add_argument("--modes", nargs="+", choices=("vortexcolumns", "eyevortex", "mouthvortex", "halo", "devilhorns"),
                        default=("vortexcolumns", "halo", "devilhorns"))
    args = parser.parse_args()
    paths = [source / "25-12-04 13-46-51 2170.jpg", source / "26-06-30 16-25-21 2963.jpg",
             source / "facu.jpeg", *source.glob("diverse-joyful-people*")]
    reports = []
    with Detector(root / "models") as detector:
        for path in paths:
            if not path.is_file():
                continue
            image = load_image(path)
            image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
            detection = detector.detect(image)
            for mode in args.modes:
                folder = root / "examples" / ("vortexcolumns" if mode.endswith("vortex") or mode == "vortexcolumns" else "headgear")
                folder.mkdir(parents=True, exist_ok=True)
                first = second = None
                error = None
                start = perf_counter()
                try:
                    first = apply_effect(image, detection, mode)
                    second = apply_effect(first, detector.detect(first), mode)
                except ValueError as exc:
                    error = str(exc)
                comparison(image, first, second, mode, error).save(folder / f"{mode}--{path.name}--comparison.jpg", quality=93)
                entry = {"source": path.name, "effect": mode, "faces": len(detection.faces),
                         "first_pass": first is not None, "second_pass": second is not None,
                         "error": error, "seconds": round(perf_counter()-start, 3)}
                reports.append(entry)
                print(entry, flush=True)
    for folder, modes in (("vortexcolumns", {"vortexcolumns", "eyevortex", "mouthvortex"}), ("headgear", {"halo", "devilhorns"})):
        entries = [entry for entry in reports if entry["effect"] in modes]
        if not entries:
            continue
        report_path = root / "examples" / folder / "report.json"
        previous = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else []
        previous = [entry for entry in previous if entry["effect"] not in args.modes]
        report_path.write_text(json.dumps(previous+entries, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
