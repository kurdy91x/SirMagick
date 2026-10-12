"""Fictional surveillance-game HUD anchored to detected faces."""
from datetime import datetime, timezone

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .chudthor import OVAL
from .effect_canvas import working, restore, points_for, text


def _overlap(a, b):
    return max(0, min(a[2], b[2])-max(a[0], b[0]))*max(0, min(a[3], b[3])-max(a[1], b[1]))


def apply_effect(image, detection):
    detection.require('face')
    canvas = working(image)
    w, h = canvas.size
    unit = min(w, h)
    # Cool camera grade, fine scanlines, and restrained edge shading.
    pixels = np.array(canvas).astype(np.float32)
    yy, xx = np.mgrid[:h, :w]
    shade = 1-.12*((xx/max(1,w)-.5)**2+(yy/max(1,h)-.5)**2)
    pixels[..., :3] = pixels[..., :3]*[.86,.94,1.05]*shade[...,None]
    pixels[::4, :, :3] *= .94
    canvas = Image.fromarray(np.uint8(np.clip(pixels,0,255)))
    hud = Image.new('RGBA', canvas.size)
    draw = ImageDraw.Draw(hud)
    margin = max(3,round(unit*.025))
    size = max(7,round(unit*.018))
    stroke = max(1,round(unit*.0025))
    boxes = []
    for face in detection.faces:
        p = points_for(face,canvas,image)[list(OVAL)]
        lo, hi = p.min(axis=0), p.max(axis=0)
        pad = (hi-lo)*[.08,.08]
        boxes.append((max(0,round(float(lo[0]-pad[0]))),max(0,round(float(lo[1]-pad[1]))),
                      min(w-1,round(float(hi[0]+pad[0]))),min(h-1,round(float(hi[1]+pad[1])))))
    header = min(h,size*3+margin*2)
    occupied = [(0,0,w,header),*boxes]
    stamp = datetime.now(timezone.utc).strftime('%Y/%m/%d %H:%M:%S UTC')
    text(draw,(w-margin,margin),stamp,size,'#d4e8e6',w*.64,'ra',1)
    draw.ellipse((margin,margin+2,margin+size*.6,margin+size*.6+2),fill='#ff304b')
    text(draw,(margin+size,margin),'REC',size,'#ff304b',w*.25,stroke=1)
    text(draw,(margin,margin+size*1.6),'OP: NIGHTWATCH / SECURE UPLINK',size*.72,'#a8c6cb',w*.7,stroke=1)
    for index, box in enumerate(boxes):
        x0,y0,x1,y1 = box
        color = '#ff364b' if index%2==0 else '#69ff83'
        draw.rectangle(box,outline=color,width=stroke)
        cx,cy = (x0+x1)/2,(y0+y1)/2
        radius = max(2,min(x1-x0,y1-y0)*.07)
        draw.line((cx-radius,cy,cx+radius,cy),fill=color,width=stroke)
        draw.line((cx,cy-radius,cx,cy+radius),fill=color,width=stroke)
        lines = [f'TRACK {index+1:02d} / TARGET ACQUIRED',
                 'VISUAL MATCH / IDENTIFIED',
                 'HQ: REQUEST CONFIRMATION' if index%2==0 else 'HQ: STAND BY / HOLD POSITION',
                 'AGENT: READY TO INTERCEPT']
        pw = min(max(1,w-margin*2),round(size*19))
        ph = min(max(1,h-header-margin),round(size*5.5))
        gap = max(5,round(unit*.018))
        offset = round((y1-y0)*.12)
        candidates = [(x1+gap,y0+offset),(x0-gap-pw,y0+offset),
                      (x1-pw*.35,y0-gap-ph),(x1-pw*.35,y1+gap)]
        candidates = [(max(0,min(w-pw,x)),max(min(header,h-ph),min(h-ph,y))) for x,y in candidates]
        px,py = min(candidates,key=lambda pos:sum(_overlap((*pos,pos[0]+pw,pos[1]+ph),b) for b in occupied))
        px,py = round(px),round(py)
        panel = (px,py,px+pw,py+ph)
        occupied.append(panel)
        if px>=x1:
            start,end = (x1,y0+offset),(px,py+ph*.35)
            bend = (px-gap*.5,end[1])
        elif px+pw<=x0:
            start,end = (x0,y0+offset),(px+pw,py+ph*.35)
            bend = (px+pw+gap*.5,end[1])
        else:
            below = py>=y1
            start = (x1-(x1-x0)*.12,y1 if below else y0)
            end = (max(px,min(px+pw,start[0]+gap)),py if below else py+ph)
            bend = (end[0],start[1]+(gap*.5 if below else -gap*.5))
        draw.line([start,bend,end],fill=color,width=stroke)
        draw.rectangle(panel,fill=(3,12,18,215),outline=color,width=stroke)
        for row,line in enumerate(lines):
            text(draw,(px+size*.5,py+size*.4+row*size*1.2),line,size*.82,
                 color if row==0 else '#c5dedb',max(1,pw-size))
    glow = hud.filter(ImageFilter.GaussianBlur(max(.5,unit*.0015)))
    glow.putalpha(glow.getchannel('A').point(lambda value:round(value*.28)))
    return restore(Image.alpha_composite(Image.alpha_composite(canvas,glow),hud),image)
