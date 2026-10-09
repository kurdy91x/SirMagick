"""Private anime comparisons; accept one image or a directory of test images."""
import argparse
import json
from pathlib import Path

from PIL import Image

from preview_modes import comparison
from sirmagick.anime import MODES, apply_effect
from sirmagick.detection import Detector
from sirmagick.images import image_paths, load_image


def preview(source, output, detector, modes):
    image = load_image(source)
    image.thumbnail((1280, 1280), Image.Resampling.LANCZOS)
    detection = detector.detect(image)
    report = {"source": source.name, "faces": len(detection.faces), "effects": {}}
    if not detection.faces:
        report["status"] = "no_face"
        return report
    output.mkdir(parents=True, exist_ok=True)
    overview = Image.new("RGB", (1800, 700*len(modes)), "#181818")
    for index, mode in enumerate(modes):
        first = apply_effect(image, detection, mode)
        error = None
        repeated_faces = 0
        try:
            repeated_detection = detector.detect(first)
            repeated_faces = len(repeated_detection.faces)
            second = apply_effect(first, repeated_detection, mode, pass_number=2)
        except ValueError as exc:
            second = None
            error = str(exc)
        assert image.size == first.size
        assert second is None or second.size == image.size
        first.save(output / f"{mode}.png")
        repeat_path = output / f"{mode}-2x.png"
        if second is not None:
            second.save(repeat_path)
        else:
            repeat_path.unlink(missing_ok=True)
        paired = comparison(image, first, second, mode, error)
        paired.save(output / f"{mode}-comparison.jpg", quality=93)
        overview.paste(paired, (0, index*700))
        report["effects"][mode] = {"first_pass": "ok", "second_pass": "ok" if second else "failed",
                                    "second_pass_faces": repeated_faces, "error": error}
    overview.save(output / "all-anime-comparison.jpg", quality=93)
    report["status"] = "ok"
    (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="Generate private anime effect comparisons")
    parser.add_argument("--source", type=Path, default=root / "examples/new-modes/original.png")
    parser.add_argument("--output", type=Path, default=root / "examples/anime")
    parser.add_argument("--modes", nargs="+", choices=MODES, default=MODES)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    if not output.is_relative_to((root / "examples").resolve()):
        parser.error("Preview output must remain under ignored examples/")
    paths = image_paths(source)
    if not paths:
        parser.error("No supported images found")
    output.mkdir(parents=True, exist_ok=True)
    reports = []
    with Detector(root / "models") as detector:
        for path in paths:
            destination = output / path.relative_to(source) if source.is_dir() else output
            try:
                report = preview(path, destination, detector, args.modes)
            except Exception as exc:
                report = {"source": path.name, "status": "failed", "error": str(exc)}
            reports.append(report)
            print(path.name, report["status"], report.get("faces", 0), "faces", flush=True)
    (output / "batch-report.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
