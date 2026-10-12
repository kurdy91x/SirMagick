"""Bounded image canvases and bundled-font drawing shared by new effects."""
from functools import lru_cache
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont


@lru_cache(maxsize=128)
def font(size):
    return ImageFont.load_default(size=max(1,round(size)))


def fit_text(draw,text,width,size,stroke=0):
    size = max(1,round(size))
    while size>1 and draw.textbbox((0,0),text,font=font(size),stroke_width=stroke)[2]>width:
        size -= 1
    return font(size)


def text(draw,xy,value,size,fill='white',width=None,anchor=None,stroke=0):
    face = fit_text(draw,value,width,size,stroke) if width else font(size)
    draw.text(xy,value,font=face,fill=fill,anchor=anchor,stroke_width=stroke,stroke_fill='black')


def wrapped(draw,xy,value,width,size,fill):
    lines = textwrap.wrap(value,width=max(8,round(width/(size*.55))),break_long_words=True)
    for index,line in enumerate(lines):
        text(draw,(xy[0],xy[1]+index*size*1.35),line,size,fill,width)
    return len(lines)*size*1.35


def working(image,max_side=1400):
    canvas = image.convert('RGBA').copy()
    canvas.thumbnail((max_side,max_side),Image.Resampling.LANCZOS)
    return canvas


def restore(canvas,image):
    if canvas.size != image.size:
        canvas = canvas.resize(image.size,Image.Resampling.LANCZOS)
    canvas = canvas.convert('RGBA')
    canvas.putalpha(image.convert('RGBA').getchannel('A'))
    return canvas


def points_for(face,canvas,image):
    return np.array([(p.x,p.y) for p in face],np.float32)*np.array([canvas.width/image.width,canvas.height/image.height],np.float32)
