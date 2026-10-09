import argparse
from contextlib import nullcontext
from dataclasses import asdict
import json
from pathlib import Path
import sys
from time import perf_counter


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Sir Magick – local CPU image detection")
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download-models", help="Download the official models")
    download.add_argument("--models", type=Path, default=Path("models"))
    detect = commands.add_parser("detect", help="Generate detection previews and JSON results")
    detect.add_argument("source", type=Path, nargs="?", default=Path("images"))
    detect.add_argument("--output", type=Path, default=Path("output"))
    detect.add_argument("--models", type=Path, default=Path("models"))
    detect.add_argument("--max-side", type=int, default=1024)
    detect.add_argument("--max-people", type=int, default=20)
    detect.add_argument("--require", choices=("any", "face", "body"), default="any")
    chudthor = commands.add_parser("chudthor", help="Large, slightly square face with small facial features")
    chudthor.add_argument("source", type=Path, nargs="?", default=Path("images"))
    chudthor.add_argument("--output", type=Path, default=Path("output-chudthor"))
    chudthor.add_argument("--models", type=Path, default=Path("models"))
    chudthor.add_argument("--max-side", type=int, default=1024)
    chudthor.add_argument("--max-people", type=int, default=20)
    chudthor.set_defaults(require="face")
    warpface = commands.add_parser("warpface", help="Enlarge the head and shrink features with local deformation")
    warpface.add_argument("source", type=Path, nargs="?", default=Path("images"))
    warpface.add_argument("--output", type=Path, default=Path("output-warpface"))
    warpface.add_argument("--models", type=Path, default=Path("models"))
    warpface.add_argument("--max-side", type=int, default=1024)
    warpface.add_argument("--max-people", type=int, default=20)
    warpface.set_defaults(require="face")
    blockface = commands.add_parser("blockface", help="Shrink the inner face and stretch the surrounding skin")
    blockface.add_argument("source", type=Path, nargs="?", default=Path("images"))
    blockface.add_argument("--output", type=Path, default=Path("output-blockface"))
    blockface.add_argument("--models", type=Path, default=Path("models"))
    blockface.add_argument("--max-side", type=int, default=1024)
    blockface.add_argument("--max-people", type=int, default=20)
    blockface.set_defaults(require="face")
    deepfry = commands.add_parser("deepfry", help="Boost colors, contrast, sharpness, and JPEG artifacts")
    deepfry.add_argument("source", type=Path, nargs="?", default=Path("images"))
    deepfry.add_argument("--output", type=Path, default=Path("output-deepfry"))
    from .effects import DESCRIPTIONS
    for name in sorted(set(DESCRIPTIONS)-{"chudthor", "warpface", "blockface", "deepfry", "random"}):
        effect_parser = commands.add_parser(name, help=DESCRIPTIONS[name])
        effect_parser.add_argument("source", type=Path, nargs="?", default=Path("images"))
        effect_parser.add_argument("--output", type=Path, default=Path("output-"+name))
        effect_parser.add_argument("--models", type=Path, default=Path("models"))
        effect_parser.add_argument("--max-side", type=int, default=1024)
        effect_parser.add_argument("--max-people", type=int, default=20)
        effect_parser.set_defaults(require="face")
    commands.add_parser("bot", help="Start the Discord bot (.env)")
    args = parser.parse_args(argv)
    try:
        if args.command == "bot":
            from .discord_bot import run_bot
            run_bot()
            return 0
        if args.command == "download-models":
            from .models import download_models
            for path in download_models(args.models):
                print(path)
            return 0
        return run_detection(args)
    except (ImportError, OSError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


def run_detection(args) -> int:
    from .images import image_paths, load_image
    from .effects import FACE_EFFECTS, DETECTION_EFFECTS, apply_effect
    processor = lambda image, detection=None: apply_effect(image, detection, args.command)
    if args.command not in DETECTION_EFFECTS and args.command != "detect":
        detector_context = lambda: nullcontext(None)
    else:
        from .detection import Detector
        if args.command == "detect":
            from .preview import render_preview
            processor = render_preview
        detector_context = lambda: Detector(args.models.resolve(), args.max_side, args.max_people)

    source, output = args.source.resolve(), args.output.resolve()
    root = source if source.is_dir() else source.parent
    if output == root or root in output.parents:
        raise ValueError("The output directory must be outside the input directory.")
    paths = image_paths(source)
    if not paths:
        raise ValueError("No supported images found.")
    output.mkdir(parents=True, exist_ok=True)
    report = []
    started = perf_counter()
    with detector_context() as detector:
        startup = perf_counter() - started if detector is not None else 0.0
        for path in paths:
            relative = path.relative_to(root)
            # Retain file extensions so foo.jpg and foo.png do not overwrite each other.
            suffix = ".preview.png" if args.command == "detect" else f".{args.command}.png"
            destination = output / relative.parent / (relative.name + suffix)
            metadata = destination.with_name(relative.name + ".json")
            entry = {"source": relative.as_posix()}
            job_started = perf_counter()
            try:
                image = load_image(path)
                if detector is None:
                    result = None
                    details = {"effect": args.command, "width": image.width, "height": image.height,
                               "requires_detection": False}
                else:
                    result = detector.detect(image)
                    if args.command in FACE_EFFECTS or args.command == "detect":
                        result.require(args.require)
                    details = asdict(result)
                destination.parent.mkdir(parents=True, exist_ok=True)
                effect_started = perf_counter()
                processed = processor(image) if result is None else processor(image, result)
                effect_seconds = perf_counter()-effect_started
                processed.save(destination)
                metadata.write_text(json.dumps(details, indent=2), encoding="utf-8")
                entry.update(status="ok", faces=len(result.faces) if result else 0,
                             bodies=len(result.poses) if result else 0,
                             detection_seconds=result.elapsed_seconds if result else 0,
                             effect_seconds=effect_seconds,
                             preview=str(destination))
                print(f"OK {relative}: effect {effect_seconds:.3f}s" if result is None else
                      f"OK {relative}: {len(result.faces)} faces, {len(result.poses)} bodies, {result.elapsed_seconds:.3f}s")
            except Exception as exc:
                # One invalid image must not prevent subsequent jobs.
                destination.unlink(missing_ok=True)
                metadata.unlink(missing_ok=True)
                entry.update(status="error", error=str(exc))
                print(f"ERROR {relative}: {exc}", file=sys.stderr)
            entry["total_seconds"] = perf_counter() - job_started
            report.append(entry)
    summary = {"command": args.command, "model_startup_seconds": startup,
               "max_people": getattr(args, "max_people", None),
               "files": report}
    (output / "report.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    failures = sum(item["status"] == "error" for item in report)
    print(f"Done: {len(report) - failures} succeeded, {failures} failed. Report: {output / 'report.json'}")
    return 1 if failures else 0
