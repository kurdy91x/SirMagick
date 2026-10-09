"""A fractured image portal with drifting mirrored shards and neon fissures."""
import cv2
import numpy as np
from PIL import Image


def apply_rift(image):
    original = image.convert('RGBA')
    work = original.copy()
    work.thumbnail((1600,1600),Image.Resampling.LANCZOS)
    pixels = np.asarray(work).astype(np.float32)/255
    pixels[...,:3] *= pixels[...,3:4]
    h,w = pixels.shape[:2]
    yy,xx = np.mgrid[:h,:w].astype(np.float32)
    scale = max(1.,min(w,h))
    x,y = (xx-w*.5)/scale,(yy-h*.48)/scale
    radius = np.hypot(x,y)
    angle = np.arctan2(y,x)
    # A handful of large irregular shards, rather than a dense mosaic.
    sector_float = (angle+np.pi)/np.pi*6+.23*np.sin(radius*9)
    sector = np.floor(sector_float).astype(np.int32)
    ring_float = radius*3.8+.15*np.sin(angle*3)
    ring = np.floor(ring_float).astype(np.int32)
    code = (sector*17+ring*31)%29
    twist = (code/28-.5)*1.25
    zoom = .66+(code%7)/9
    sample_angle = angle+twist+.32*np.sin(radius*8)
    # Alternate reflected shards and magnified image echoes.
    sx = np.cos(sample_angle)*radius/zoom
    sy = np.sin(sample_angle)*radius/zoom
    sx = np.where(code%3 == 0,-sx,sx)
    sx += np.sin(code*2.1)*.12
    sy += np.cos(code*1.7)*.12
    mx,my = np.float32(sx*scale+w*.5),np.float32(sy*scale+h*.48)
    warped = cv2.remap(pixels,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    a = warped[...,3:4]
    rgb = warped[...,:3]/np.maximum(a,1e-6)
    # White hot cyan/magenta seams separate fragments, with a black central tear.
    sf = sector_float-sector
    rf = ring_float-ring
    seams = ((np.minimum(sf,1-sf)<.012)|(np.minimum(rf,1-rf)<.014)).astype(np.float32)
    core = np.abs(x-.055*np.sin(y*12)-.025*np.sin(y*31))
    tear = np.clip((core-.012)/.026,0,1)
    seam_color = np.stack((.5+.5*np.sin(angle*2),np.full_like(x,.7),np.ones_like(x)),axis=-1)
    glow = cv2.GaussianBlur(seams,(0,0),max(1.,scale*.005))
    edge = np.exp(-np.square((core-.025)/.012))
    rgb = rgb*(.75+.25*np.cos(radius*15))[...,None]*tear[...,None]
    rgb += seam_color*(seams*.8+glow*1.8+edge*.75)[...,None]
    result = Image.fromarray(np.uint8(np.clip(rgb*255,0,255)))
    if result.size != original.size:
        result = result.resize(original.size,Image.Resampling.LANCZOS)
    result = result.convert('RGBA')
    result.putalpha(original.getchannel('A'))
    return result
