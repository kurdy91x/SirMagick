"""Private original / first / second pass reviews for photo Wojaks and Giraffe."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
from sirmagick.detection import Detector
from sirmagick.effects import apply_effect
from sirmagick.images import load_image


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source',type=Path,default=Path('examples/testimages'))
    parser.add_argument('--crop-top',type=float,default=1.,help='Keep this fraction of image height for an upper-body crop')
    parser.add_argument('--max-side',type=int,default=1000)
    parser.add_argument('--prefix',help='Optional filename prefix')
    parser.add_argument('--inputs',nargs='+',help='Input filenames relative to --source')
    parser.add_argument('--output',type=Path,default=Path('examples/wojak-review'))
    parser.add_argument('--modes',nargs='+',choices=('soyjak','wojak_chud','wojak_doomer','brainlet','wojak_npc','wojak_npcangry','giraffe'),
                        default=['wojak_doomer','brainlet','wojak_npc','wojak_npcangry','giraffe'])
    args = parser.parse_args()
    if not 0<args.crop_top<=1 or args.max_side<128:
        parser.error('--crop-top must be in (0,1], and --max-side at least 128')
    args.output.mkdir(parents=True,exist_ok=True)
    names = args.inputs or ('facu.jpeg','26-06-30 16-25-21 2963.jpg','25-12-04 15-10-24 2173.jpg')
    with Detector(Path('models')) as detector:
        for number,name in enumerate(names,1):
            original = load_image(args.source/name)
            if args.crop_top<1:
                original = original.crop((0,0,original.width,round(original.height*args.crop_top)))
            original.thumbnail((args.max_side,args.max_side),Image.Resampling.LANCZOS)
            detection = detector.detect(original,segmentation="giraffe" in args.modes)
            if not detection.faces:
                print('Skipped (no face):',name,flush=True)
                continue
            for mode in args.modes:
                stem = f'{args.prefix or mode}-{number}'
                first = apply_effect(original,detection,mode)
                first.save(args.output/f'{stem}-1x.png')
                second = None
                error = None
                try:
                    second = apply_effect(first,detector.detect(first,segmentation=mode=="giraffe"),mode)
                    second.save(args.output/f'{stem}-2x.png')
                except ValueError as exc:
                    error = str(exc)
                sheet = Image.new('RGB',(1350,700),(25,25,25))
                draw = ImageDraw.Draw(sheet)
                for col,(label,picture) in enumerate((('Original',original),('1x',first),('2x',second))):
                    draw.text((col*450+12,10),label,fill='white')
                    if picture is None:
                        draw.text((col*450+12,45),error or 'Failed',fill='white')
                        continue
                    picture = picture.convert('RGB')
                    picture.thumbnail((430,650),Image.Resampling.LANCZOS)
                    sheet.paste(picture,(col*450+(450-picture.width)//2,35+(650-picture.height)//2))
                sheet.save(args.output/f'{stem}-comparison.jpg',quality=94)
                print(mode,number,original.size,first.size,second.size if second else error,flush=True)
    print('Review:',args.output.resolve())


if __name__=='__main__':
    main()
