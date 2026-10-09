"""Private three-column comparisons for cinematic and meme effects."""
import json
import argparse
from contextlib import nullcontext
from pathlib import Path

from PIL import Image
from preview_modes import comparison
from sirmagick.detection import Detector
from sirmagick.effects import apply_effect
from sirmagick.images import load_image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modes', nargs='+', choices=('thermal','nightvision','thanos','dealwithit','tron','rift'),
                        default=('thermal','nightvision','thanos','dealwithit','tron','rift'))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root/'examples/testimages'
    paths = [source/'facu.jpeg', source/'26-06-30 16-25-21 2963.jpg',
             source/'25-12-04 13-46-51 2170.jpg', *source.glob('diverse-joyful-people*')]
    output = root/'examples/cinematic'
    output.mkdir(parents=True, exist_ok=True)
    report = []
    detected_modes = {'dealwithit','tron'}
    with Detector(root/'models') if detected_modes.intersection(args.modes) else nullcontext() as detector:
        for path in paths:
            if not path.is_file():
                continue
            image = load_image(path)
            image.thumbnail((1280,1280), Image.Resampling.LANCZOS)
            detection = detector.detect(image) if detector else None
            for mode in args.modes:
                first = second = None
                error = None
                try:
                    first = apply_effect(image, detection if mode in detected_modes else None, mode)
                    second = apply_effect(first, detector.detect(first) if mode in detected_modes else None, mode)
                except ValueError as exc:
                    error = str(exc)
                comparison(image, first, second, mode, error).save(output/f'{mode}--{path.name}--comparison.jpg',quality=94)
                if first is not None:
                    destination = output/f'{mode}--{path.name}--1x.png'
                    temporary = destination.with_suffix('.tmp.png')
                    first.save(temporary)
                    temporary.replace(destination)
                entry = dict(source=path.name,mode=mode,faces=len(detection.faces) if detection else None,first_pass=first is not None,
                             second_pass=second is not None,error=error)
                report.append(entry)
                print(entry, flush=True)
    report_path = output/'report.json'
    previous = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else []
    previous = [entry for entry in previous if entry['mode'] not in args.modes]
    report_path.write_text(json.dumps(previous+report,indent=2),encoding='utf-8')


if __name__ == '__main__':
    main()
