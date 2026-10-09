"""Vorher/nachher-Beispiele aus einem erfolgreichen chudthor-Batch exportieren."""

import json
import argparse
from pathlib import Path
import shutil

from PIL import Image, ImageDraw, ImageOps

from .images import load_image


def export_examples(source=Path("images"), results=None,
                    destination=None, effect="chudthor"):
    if effect not in {"chudthor", "warpface", "blockface", "deepfry"}:
        raise ValueError("Unbekannter Beispieleffekt.")
    results = Path(results) if results is not None else Path(f"output-{effect}")
    destination = Path(destination) if destination is not None else Path("examples")/effect
    report = json.loads((results / "report.json").read_text(encoding="utf-8"))
    successful = [entry for entry in report["files"] if entry["status"] == "ok"]
    if not successful:
        raise ValueError("Keine erfolgreichen Beispiele zum Exportieren.")
    destination.mkdir(parents=True, exist_ok=True)
    sheet = Image.new("RGB", (1200, ((len(successful)+1)//2)*350), "#202020")
    draw = ImageDraw.Draw(sheet)
    for i, entry in enumerate(successful):
        relative = Path(entry["source"])
        processed = results / relative.parent / (relative.name + f".{effect}.png")
        target = destination / relative.parent / processed.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(processed, target)
        x, y = (i%2)*600, (i//2)*350
        for offset, path, label in ((0, source/relative, "Original"), (300, processed, effect.capitalize())):
            rgba = load_image(path)
            background = Image.new("RGB", rgba.size, "#303030")
            background.paste(rgba, mask=rgba.getchannel("A"))
            thumb = ImageOps.contain(background, (290, 300))
            sheet.paste(thumb, (x+offset+(290-thumb.width)//2, y+25+(300-thumb.height)//2))
            draw.text((x+offset+5, y+5), label, fill="white")
        draw.text((x+5, y+330), relative.as_posix()[:75], fill="white")
    sheet.save(destination / "vergleich.jpg", quality=92)
    shutil.copyfile(results / "report.json", destination / "report.json")
    print(f"{len(successful)} Beispiele: {destination / 'vergleich.jpg'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Vorher/nachher-Beispiele exportieren")
    parser.add_argument("--effect", choices=("chudthor", "warpface", "blockface", "deepfry"), default="chudthor")
    args = parser.parse_args()
    export_examples(effect=args.effect)
