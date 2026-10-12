"""CPU album cover artwork with three procedural, distressed logo styles."""
import hashlib
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps, ImageFont

from .effect_canvas import text
from .effect_options import metal_parts

MODES = ('metalcover','blackmetalcover','deathmetalcover')
FONTS = {'metalcover':'Metal Lord.otf',
         'blackmetalcover':'Dystopian-Canticle-Regular.otf',
         'deathmetalcover':'ArtDystopia.ttf'}


@lru_cache(maxsize=100)
def _font(style,size):
    return ImageFont.truetype(str(Path(__file__).parent/'assets'/'font'/FONTS[style]),size)


def _logo(band,style,rng):
    mask = Image.new('L',(820,240))
    draw = ImageDraw.Draw(mask)
    size = 110
    while size>5 and draw.textbbox((0,0),band,font=_font(style,size))[2]>720:
        size -= 1
    face = _font(style,size)
    draw.text((410,118),band,font=face,fill=255,anchor='mm')
    # Tall narrow glyphs provide a compact base for the custom silhouette.
    box = mask.getbbox()
    if box is None:
        raise ValueError('The band name contains no supported visible characters.')
    glyphs = mask.crop(box).resize((720,85 if style=='deathmetalcover' else 150 if style=='blackmetalcover' else 115),Image.Resampling.LANCZOS)
    if style=='blackmetalcover':
        glyphs = glyphs.filter(ImageFilter.MinFilter(3))
    elif style=='deathmetalcover':
        glyphs = glyphs.filter(ImageFilter.MaxFilter(3))
    mask = Image.new('L',(820,240))
    mask.paste(glyphs,(50,65))
    draw = ImageDraw.Draw(mask)
    pixels = np.array(mask)
    columns = np.flatnonzero(pixels.max(axis=0)>220)
    for x in columns[::9 if style=='blackmetalcover' else 15]:
        rows = np.flatnonzero(pixels[:,x]>220)
        if not len(rows):
            continue
        for y,side in ((int(rows[0]),-1),(int(rows[-1]),1)):
            length = float(rng.uniform(18,57))
            dx = float(rng.uniform(-19,19))
            if style=='metalcover':
                draw.polygon([(int(x)-4,y),(int(x)+4,y),(int(x+dx),int(y+side*length))],fill=255)
            elif style=='blackmetalcover':
                end = (int(x+dx),int(y+side*length))
                mid = (int(x-dx*.25),int(y+side*length*.5))
                draw.line([(int(x),y),mid,end],fill=255,width=2)
                draw.line([mid,(mid[0]+int(rng.uniform(-18,18)),mid[1]+side*18)],fill=230,width=1)
            else:
                for step in range(3):
                    yy = y+side*(step*9+5)
                    draw.polygon([(int(x)-6,yy),(int(x)+6,yy),(int(x+dx),int(yy+side*18))],fill=255)
    # Mirrored extensions create a deliberate band-logo silhouette.
    for side in (-1,1):
        root = 410+side*340
        if style=='blackmetalcover':
            for offset in (0,20,40):
                draw.line([(root,100+offset),(root+side*25,70+offset),(root+side*43,18+offset)],fill=255,width=2)
        elif style=='metalcover':
            draw.polygon([(root,95),(root+side*46,32),(root+side*23,130),(root,155)],fill=255)
        else:
            draw.line([(root,90),(root+side*30,105),(root+side*43,160),(root+side*18,142)],fill=255,width=5)
    # Cut fine cracks through the lettering rather than reducing bit depth.
    for _ in range(95 if style=='deathmetalcover' else 35):
        x,y = int(rng.integers(45,775)),int(rng.integers(60,190))
        draw.line((x,y,x+int(rng.integers(-9,10)),y+int(rng.integers(4,20))),fill=0,width=1)
    return mask


def apply_effect(image,mode,value):
    if mode not in MODES:
        raise ValueError('Unknown metal cover style.')
    band,album = metal_parts(value)
    seed = int.from_bytes(hashlib.sha256((band+'|'+mode).encode()).digest()[:8],'little')
    rng = np.random.default_rng(seed)
    base = ImageOps.fit(image.convert('RGB'),(900,900),Image.Resampling.LANCZOS)
    gray = ImageOps.autocontrast(ImageOps.grayscale(base),cutoff=2)
    gray = ImageEnhance.Contrast(gray).enhance(2.5 if mode=='blackmetalcover' else 1.6)
    pixels = np.asarray(gray,dtype=np.float32)
    yy,xx = np.mgrid[:900,:900].astype(np.float32)
    edge = np.clip(1-.60*((xx-450)**2+(yy-450)**2)/450**2,.12,1)
    bands = 1-.75*np.exp(-(yy/160)**2)-.65*np.exp(-((900-yy)/100)**2)
    pixels = np.clip(pixels*edge*bands+rng.normal(0,18 if mode=='blackmetalcover' else 8,pixels.shape),0,255)
    if mode=='blackmetalcover':
        # Harsh xerox-like ink with sparse gray, distinct from the photographic style.
        pixels = np.where(pixels>140,230,np.where(pixels>75,85,8))
        canvas = Image.fromarray(np.uint8(pixels)).convert('RGB')
    elif mode=='deathmetalcover':
        ink = pixels[...,None]*np.array([.75,.24,.20],np.float32)+np.array([8,0,1],np.float32)
        canvas = Image.fromarray(np.uint8(np.clip(ink,0,255)))
    else:
        canvas = Image.fromarray(np.uint8(pixels)).convert('RGB')
    draw = ImageDraw.Draw(canvas)
    for _ in range(110):
        x,y = (int(v) for v in rng.integers(0,900,2))
        length = int(rng.integers(3,100))
        color = (int(rng.integers(15,85)),)*3
        draw.line((x,y,x+int(rng.integers(-8,9)),y+length),fill=color,width=1)
    logo = _logo(band.upper(),mode,rng)
    # A thin dark outline retains the logo over bright image details.
    canvas.paste((0,0,0),(40,15),logo.filter(ImageFilter.MaxFilter(5)))
    canvas.paste((200,174,151) if mode=='deathmetalcover' else (232,232,222),(40,15),logo)
    draw = ImageDraw.Draw(canvas)
    title = '  '.join(album.upper())
    text(draw,(450,850),title,22,'#c6c6bd',800,'mm',1)
    draw.line((330,817,570,817),fill='#77776f',width=1)
    return canvas.convert('RGBA')
