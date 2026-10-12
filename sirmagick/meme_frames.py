"""Local image-only meme layouts, supplied wordmarks, and procedural graphics."""
from functools import lru_cache
from pathlib import Path
import secrets
import textwrap

import numpy as np
import cv2
from PIL import Image,ImageDraw,ImageEnhance,ImageFilter,ImageOps

from .effect_canvas import font,fit_text,text,wrapped,working,restore
from .effect_options import achievement_parts

MODES = ('combobreaker','youdied','wasted','animerays','achievement','chanpost','hodl','buythedip','kaliyuga','hornijail')
ASSETS = ('anime.rays.jpg','wasted.gta.jpg','youdied.souls.jpg')


@lru_cache(maxsize=3)
def _asset(name):
    with Image.open(Path(__file__).parent/'assets'/name) as source:
        pixels = np.array(source.convert('RGBA'))
    # The supplied JPGs have white backgrounds, not actual alpha channels.
    whiteness = pixels[...,:3].min(axis=-1).astype(np.float32)
    pixels[...,3] = np.uint8(np.clip((250-whiteness)/35,0,1)*255)
    if name=='anime.rays.jpg':
        gray = pixels[...,:3].astype(np.float32).mean(axis=-1)
        pixels[...,3] = np.uint8(255-gray)
        pixels[...,:3] = 0
    overlay = Image.fromarray(pixels)
    if name!='anime.rays.jpg':
        overlay = overlay.crop(overlay.getbbox())
    return overlay


def _post_ids(rng,count):
    result = []
    while len(result)<count:
        repeats = int(rng.choice([2,2,2,3,3,4,5]))
        digit = str(int(rng.integers(1,10)))
        number = str(int(rng.integers(10000,100000)))+digit*repeats
        if number not in result:
            result.append(number)
    return result


def _chanpost(image,rng):
    # A fixed-size fake screenshot, never a network request.
    canvas = Image.new('RGB',(1200,820),'#ffffee')
    draw = ImageDraw.Draw(canvas)
    ids = _post_ids(rng,4)
    text(draw,(18,12),'File: image.jpg (249 KB, original image)',17,'#b80000')
    thumb = ImageOps.contain(image.convert('RGB'),(370,520),Image.Resampling.LANCZOS)
    canvas.paste(thumb,(22,48))
    text(draw,(420,20),'Anonymous',20,'#117743')
    text(draw,(550,23),f'10/12/26(Mon)20:00:00 No.{ids[0]}',15,'#b80000',620)
    text(draw,(22,605),'Imageboard simulator',14,'#789922')
    choices = ['>be me\n>open image\n>immediately regret having eyes',
               'this is what peak performance looks like',
               '>another perfectly normal day on the internet',
               'the simulation budget has been reduced again',
               'someone spent actual electricity making this',
               'many such cases. extremely normal. carry on.']
    for index,y in enumerate((68,302,536),1):
        draw.rectangle((420,y,1180,y+212),fill='#f0e0d6',outline='#d9bfb7')
        text(draw,(430,y+9),'Anonymous',18,'#117743')
        text(draw,(560,y+11),f'10/12/26(Mon)20:00:0{index} No.{ids[index]}',14,'#b80000',600)
        text(draw,(440,y+42),'>>'+ids[index-1]+(' (OP)' if index==1 else ''),17,'#0000aa')
        phrase = str(rng.choice(choices))
        for offset,line in enumerate(phrase.splitlines()):
            text(draw,(440,y+72+offset*25),line,20,'#789922' if line.startswith('>') else '#800000',710)
        suffix = ids[index-1]
        count = len(suffix)-len(suffix.rstrip(suffix[-1]))
        check = 'check em' if count==2 else 'nice trips' if count==3 else 'quads confirmed' if count==4 else 'quints. what are the odds.'
        text(draw,(440,y+169),check,18,'#800000',490)
        if index>1:
            source = image.convert('RGB')
            left,top,right,bottom = (.08,.12,.56,.60) if index==2 else (.46,.42,.94,.90)
            box = (int(source.width*left),int(source.height*top),max(int(source.width*left)+1,int(source.width*right)),max(int(source.height*top)+1,int(source.height*bottom)))
            crop = ImageOps.fit(source.crop(box),(92,120),Image.Resampling.LANCZOS)
            canvas.paste(crop,(1068,y+62))
    return canvas.convert('RGBA')


def _achievement(image,value):
    title,description = achievement_parts(value)
    w,h = 1200,650
    yy,xx = np.mgrid[:h,:w]
    field = (xx/w*.55+(1-yy/h)*.45)[...,None]
    rgb = np.array([5,33,62])*(1-field)+np.array([44,170,176])*field
    canvas = Image.fromarray(np.uint8(rgb))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((48,75,1152,360),fill='#1c282e')
    text(draw,(80,98),'ACHIEVEMENTS',30,'#66a6ba')
    draw.rectangle((85,165,259,339),fill='white')
    icon = ImageOps.fit(image.convert('RGB'),(160,160),Image.Resampling.LANCZOS)
    canvas.paste(icon,(92,172))
    text(draw,(285,173),title,34,'#eeeeee',820)
    description_size = 24
    while description_size>12 and len(textwrap.wrap(description,width=max(8,round(800/(description_size*.55)))))*description_size*1.35>110:
        description_size -= 1
    wrapped(draw,(285,227),description,800,description_size,'#b8bfc4')
    draw.rectangle((48,382,1152,566),fill='#1c282e')
    draw.rectangle((83,415,1117,459),outline='#65727a',width=1)
    draw.rectangle((92,424,1108,450),fill='#254b6c')
    text(draw,(82,492),'Achievement unlocked. Absolutely deserved.',28,'#dddddd',1030)
    return canvas.convert('RGBA')


def _hornijail(image):
    # This supplied JPEG has white window panes instead of an alpha channel.
    # Only the three explicit pane polygons are replaced; white lettering stays.
    with Image.open(Path(__file__).parent/'assets'/'horni.jail.jpg') as asset:
        frame = np.array(asset.convert('RGBA'))
    h,w = frame.shape[:2]
    scale = np.array([w/932,h/810],np.float32)
    destination = np.float32([(202,159),(570,49),(576,310),(195,405)])*scale
    photo = np.array(ImageOps.fit(image.convert('RGB'),(400,350),Image.Resampling.LANCZOS))
    matrix = cv2.getPerspectiveTransform(np.float32([(0,0),(399,0),(399,349),(0,349)]),destination)
    warped = cv2.warpPerspective(photo,matrix,(w,h),flags=cv2.INTER_CUBIC,borderMode=cv2.BORDER_REPLICATE)
    mask = np.zeros((h,w),np.uint8)
    for pane in (((210,162),(293,136),(289,377),(197,403)),
                 ((337,120),(427,92),(430,344),(333,372)),
                 ((466,78),(569,50),(576,309),(468,337))):
        cv2.fillConvexPoly(mask,np.int32(np.array(pane)*scale),255,lineType=cv2.LINE_AA)
    weight = mask[...,None]/255
    frame[...,:3] = np.uint8(frame[...,:3]*(1-weight)+warped*weight)
    return Image.fromarray(frame)


def _coin(draw,x,y,r):
    draw.ellipse((x-r,y-r,x+r,y+r),fill='#ed9b12',outline='#ffd97d',width=max(1,round(r*.09)))
    draw.ellipse((x-r*.79,y-r*.79,x+r*.79,y+r*.79),outline='#a56400',width=max(1,round(r*.04)))
    text(draw,(x,y),'B',r*1.35,'#fff0af',anchor='mm')
    for offset in (-.12,.12):
        draw.line((x+r*offset,y-r*.68,x+r*offset,y+r*.68),fill='#fff0af',width=max(1,round(r*.045)))


def apply_effect(image,mode,value=None,seed=None):
    if mode not in MODES:
        raise ValueError('Unknown meme layout.')
    rng = np.random.default_rng(secrets.randbits(64) if seed is None else seed)
    if mode=='hornijail':
        return _hornijail(image)
    if mode=='achievement':
        return _achievement(image,value)
    if mode=='chanpost':
        return _chanpost(image,rng)
    canvas = working(image)
    w,h = canvas.size
    unit = min(w,h)
    if mode=='animerays':
        canvas = Image.alpha_composite(canvas,_asset('anime.rays.jpg').resize(canvas.size,Image.Resampling.LANCZOS))
    elif mode in ('youdied','wasted'):
        base = ImageOps.grayscale(canvas).convert('RGBA') if mode=='wasted' else canvas
        canvas = ImageEnhance.Brightness(base).enhance(.47 if mode=='youdied' else .62)
        band = Image.new('RGBA',canvas.size)
        draw = ImageDraw.Draw(band)
        draw.rectangle((0,h*.39,w,h*.62),fill=(0,0,0,110))
        canvas = Image.alpha_composite(canvas,band)
        overlay = _asset('youdied.souls.jpg' if mode=='youdied' else 'wasted.gta.jpg').copy()
        target = (max(1,round(w*(.82 if mode=='youdied' else .58))),max(1,round(h*.20)))
        ratio = min(target[0]/overlay.width,target[1]/overlay.height)
        overlay = overlay.resize((max(1,round(overlay.width*ratio)),max(1,round(overlay.height*ratio))),Image.Resampling.LANCZOS)
        canvas.alpha_composite(overlay,((w-overlay.width)//2,(h-overlay.height)//2))
    elif mode=='combobreaker':
        layer = Image.new('RGBA',(max(1,w),max(1,round(h*.32))))
        draw = ImageDraw.Draw(layer)
        text(draw,(layer.width/2,layer.height/2),'C-C-C-COMBOBREAKER',unit*.12,'#fff23b',w*.94,'mm',max(1,round(unit*.007)))
        layer = layer.rotate(7,Image.Resampling.BICUBIC,expand=True)
        canvas.alpha_composite(layer,((w-layer.width)//2,round(h*.48-layer.height/2)))
    elif mode in ('hodl','buythedip'):
        tint = Image.new('RGBA',canvas.size,(255,119,0,55) if mode=='hodl' else (70,0,18,55))
        canvas = Image.alpha_composite(canvas,tint)
        draw = ImageDraw.Draw(canvas)
        rising = mode=='hodl'
        xs = np.linspace(w*.04,w*.96,24)
        trend = np.linspace(.8,.18,24) if rising else np.linspace(.15,.82,24)
        ys = (trend+rng.uniform(-.06,.06,24))*h
        points = [(float(x),float(y)) for x,y in zip(xs,ys)]
        color = '#20ff4b' if rising else '#ff193e'
        draw.line(points,fill='#101010',width=max(3,round(unit*.018)))
        draw.line(points,fill=color,width=max(2,round(unit*.010)))
        end = np.array(points[-1]); prev = np.array(points[-2]); direction = end-prev; direction /= max(1.,np.linalg.norm(direction))
        normal = np.array([-direction[1],direction[0]])
        draw.polygon([tuple(end+direction*unit*.035),tuple(end-direction*unit*.045+normal*unit*.035),tuple(end-direction*unit*.045-normal*unit*.035)],fill=color)
        for _ in range(6 if rising else 3):
            _coin(draw,float(rng.uniform(.1,.9)*w),float(rng.uniform(.12,.85)*h),max(3,unit*.055))
        phrase = str(rng.choice(['HODL','STILL EARLY','HAVE FUN STAYING POOR'] if rising else ['BUY THE DIP','HEALTHY CORRECTION','ZOOM OUT']))
        text(draw,(w/2,h*.08),phrase,unit*.11,'#fff0a0',w*.94,'mm',max(1,round(unit*.004)))
        text(draw,(w/2,h*.91),'+420.69% | TO THE MOON' if rising else '-97.8% | NOTHING TO WORRY ABOUT',unit*.06,color,w*.94,'mm',max(1,round(unit*.003)))
        if rising:
            # A small drawn rocket follows the chart's upward direction.
            x,y = w*.80,h*.22
            draw.polygon([(x,y-unit*.10),(x-unit*.035,y+unit*.03),(x+unit*.035,y+unit*.03)],fill='white',outline='#303030')
            draw.ellipse((x-unit*.014,y-unit*.055,x+unit*.014,y-unit*.027),fill='#56d5ff')
            draw.polygon([(x-unit*.022,y+unit*.03),(x,y+unit*.10),(x+unit*.022,y+unit*.03)],fill='#ff5c14')
        else:
            thumb = ImageOps.fit(image.convert('RGBA'),(max(1,round(unit*.17)),max(1,round(unit*.17))),Image.Resampling.LANCZOS)
            canvas.alpha_composite(thumb,(round(w*.04),round(h*.65)))
    else:
        canvas = ImageEnhance.Contrast(canvas).enhance(1.12)
        draw = ImageDraw.Draw(canvas)
        bands = ((.02,.15,'#aa0017','THERE ARE 426,877 YEARS LEFT IN THE KALI YUGA'),
                 (.74,.09,'#f1e5b5','KALI YUGA KALI YUGA KALI YUGA'),
                 (.84,.07,'#b00014','KALI YUGA KALI YUGA KALI YUGA'),
                 (.93,.07,'#12263a','KALI YUGA KALI YUGA KALI YUGA'))
        for y,size,color,phrase in bands:
            draw.rectangle((0,h*y,w,h*(y+size)),fill=color)
            text(draw,(w/2,h*(y+size/2)),phrase,h*size*.46,'#171717' if color=='#f1e5b5' else 'white',w*.96,'mm')
        draw.rectangle((w*.03,h*.20,w*.29,h*.27),fill='#bd0019')
        text(draw,(w*.16,h*.235),'LIVE',unit*.045,'white',w*.22,'mm')
        text(draw,(w*.97,h*.69),'BREAKING NEWS | SPECIAL REPORT',unit*.05,'white',w*.94,'rm',1)
    return restore(canvas,image)
