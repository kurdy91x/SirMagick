"""Generate a flat private review folder for the new effect batch."""
import argparse
import html
import json
from pathlib import Path
import sys
from time import perf_counter

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image
from preview_modes import comparison
from sirmagick.detection import Detector
from sirmagick.effects import TRANSFORMERS,FACE_MASKS,MEMES,STYLIZED,FACE_EFFECTS,apply_effect
from sirmagick.images import image_paths,load_image

MODES = tuple(sorted(TRANSFORMERS|FACE_MASKS|MEMES|STYLIZED|{'surveillance'}))
ACHIEVEMENT_TEXT = 'TouchGrass Finally went outside. The graphics were surprisingly good.'


def index(output,report):
    cards = []
    for entry in sorted(report,key=lambda e:(e['mode'],e['input'])):
        label = html.escape(entry['mode']+' / '+str(entry['input']))
        file = html.escape(entry['comparison'],quote=True)
        note = html.escape(entry['error'] or 'Both passes completed')
        cards.append(f'<article data-mode="{entry["mode"]}"><h2>{label}</h2><a href="{file}"><img loading="lazy" src="{file}"></a><p>{note}</p></article>')
    options = ''.join(f'<option>{mode}</option>' for mode in sorted({e['mode'] for e in report}))
    page = '''<!doctype html><meta charset="utf-8"><title>SirMagick private review</title>
<style>body{background:#17191f;color:#eee;font:16px system-ui;margin:28px}select{font:inherit;padding:8px}article{margin:25px 0;background:#222630;padding:14px;border-radius:9px}img{width:100%;max-width:1800px}h2{font-size:18px}p{color:#aab1c0}</style>
<h1>New effects - private review</h1><p>Original / first pass / second pass. Click a comparison for full size. No images are tracked or included in Docker.</p>
<select id="filter"><option value="">All effects</option>'''+options+'''</select>'''+''.join(cards)+'''
<script>document.querySelector('#filter').onchange=function(){document.querySelectorAll('article').forEach(a=>a.hidden=this.value&&a.dataset.mode!==this.value)}</script>'''
    (output/'index.html').write_text(page,encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--modes',nargs='+',choices=MODES,default=MODES)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source = root/'examples/testimages'
    output = root/'examples/new-effects'
    output.mkdir(parents=True,exist_ok=True)
    report_path = output/'report.json'
    report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else []
    report = [entry for entry in report if entry['mode'] not in args.modes and entry['mode'] in MODES]
    with Detector(root/'models') as detector:
        candidates = []
        for path in image_paths(source):
            image = load_image(path)
            image.thumbnail((1280,1280),Image.Resampling.LANCZOS)
            detection = detector.detect(image)
            bodies = sum(all(pose[i].visibility>.5 for i in (11,12,23,24)) for pose in detection.poses)
            candidates.append((path,image,detection,bodies))
            print('Input:',path.name,'faces',len(detection.faces),'torsos',bodies,flush=True)
        selected = [next(item for item in candidates if item[0].name==name)
                    for name in ('facu.jpeg','26-06-30 16-25-21 2963.jpg')]
        remaining = [item for item in candidates if item[0] not in {s[0] for s in selected} and item[2].faces]
        body = max(remaining,key=lambda item:(item[3],len(item[2].faces)))
        selected.append(body)
        remaining = [item for item in remaining if item[0] != body[0]]
        selected.append(max(remaining,key=lambda item:(len(item[2].faces),item[3])))
        for number,(path,image,detection,bodies) in enumerate(selected,1):
            image.save(output/f'input-{number}.png')
            for mode in args.modes:
                first = second = None
                error = None
                start = perf_counter()
                try:
                    first = apply_effect(image,detection if mode in FACE_EFFECTS else None,mode,text=ACHIEVEMENT_TEXT)
                    first.save(output/f'{mode}--{number}--1x.png')
                    second_detection = detector.detect(first) if mode in FACE_EFFECTS else None
                    second = apply_effect(first,second_detection,mode,text=ACHIEVEMENT_TEXT)
                except Exception as exc:
                    error = f'{type(exc).__name__}: {exc}'
                filename = f'{mode}--{number}--comparison.jpg'
                comparison(image,first,second,mode,error).save(output/filename,quality=94)
                entry = dict(mode=mode,input=number,source=path.name,faces=len(detection.faces),torsos=bodies,
                             first_pass=first is not None,second_pass=second is not None,error=error,
                             seconds=round(perf_counter()-start,3),comparison=filename)
                report.append(entry)
                print(mode,number,'1x',entry['first_pass'],'2x',entry['second_pass'],entry['seconds'],error or '',flush=True)
                report_path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    index(output,report)
    print('Review:',output/'index.html',flush=True)


if __name__=='__main__':
    main()
