"""Recognizable photo Wojaks using local remaps and face-bound color masks."""
from functools import lru_cache
import cv2
import numpy as np
from PIL import Image, ImageDraw

from .chudthor import OVAL
from .warpface import EYES, MOUTH
from .effect_canvas import working, restore, points_for

MODES = ('wojak_doomer','brainlet','wojak_npc','wojak_npcangry')


def _round_line(draw,points,width):
    points = [tuple(p) for p in points]
    draw.line(points,fill=(12,12,12,255),width=width,joint='curve')
    r = width/2
    for x,y in points:
        draw.ellipse((x-r,y-r,x+r,y+r),fill=(12,12,12,255))


@lru_cache(maxsize=1)
def _cigarette():
    from .dealwithit import _asset
    pixels = _asset('cig.leftside.jpg').copy()
    # Remove only connected exterior white, preserving white paper inside outlines.
    white = np.uint8(pixels[...,:3].min(axis=-1)>242)
    _, labels = cv2.connectedComponents(white)
    border = np.unique(np.concatenate((labels[0],labels[-1],labels[:,0],labels[:,-1])))
    border = border[border!=0]
    exterior = np.isin(labels,border)
    pixels[exterior,3] = 0
    edge = cv2.dilate(np.uint8(exterior),np.ones((3,3),np.uint8)).astype(bool)&~exterior
    pixels[edge,3] = np.uint8(np.clip((255-pixels[edge,:3].min(axis=-1).astype(float))/35,0,1)*255)
    return pixels


def apply_effect(image,detection,mode):
    from .face_transformers import warp_region
    if mode not in MODES:
        raise ValueError('Unknown Wojak effect.')
    expression = 'angry' if mode=='wojak_npcangry' else 'resigned'
    mode = {'wojak_doomer':'doomer','wojak_npc':'npc','wojak_npcangry':'npc'}.get(mode,mode)
    detection.require('face')
    canvas = working(image,1200)
    pixels = np.array(canvas)
    for face in detection.faces:
        p = points_for(face,canvas,image)
        axis = p[263]-p[33]
        axis /= max(1.,float(np.linalg.norm(axis)))
        down = np.array([-axis[1],axis[0]],np.float32)
        width = max(8.,float(np.ptp(p[list(OVAL)]@axis)))
        if mode=='brainlet':
            origin = (p[33]+p[263])/2
            yy,xx = np.mgrid[:pixels.shape[0],:pixels.shape[1]].astype(np.float32)
            dx,dy = xx-origin[0],yy-origin[1]
            u,v = dx*axis[0]+dy*axis[1],dx*down[0]+dy*down[1]
            upper = np.clip((-v/width-.055)/.22,0,1)
            upper = upper*upper*(3-2*upper)
            support = np.exp(-(u/(width*.65))**6)*np.exp(-(v/(width*.95))**6)
            weight = upper*support
            su = u/(1-.15*weight)
            sv = v/(1-.43*weight)
            mx = np.float32(origin[0]+su*axis[0]+sv*down[0])
            my = np.float32(origin[1]+su*axis[1]+sv*down[1])
            pixels = cv2.remap(pixels,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
            continue
        if mode=='doomer':
            for eye in EYES:
                warp_region(pixels,p[list(eye)],1.,.60,axis=axis,padding=(1.15,1.8))
            for corner in (61,291):
                region = p[corner]+np.array([[-1,-1],[1,1]],np.float32)*width*.055
                warp_region(pixels,region,1,1,shift=(0,width*.035),axis=axis)
        mask = np.zeros(pixels.shape[:2],np.uint8)
        contour = p[list(OVAL)].copy()
        eye_center = (p[33]+p[263])/2
        above = np.clip(-((contour-eye_center)@down)/(width*.40),0,1)
        contour -= above[:,None]**2*down*width*.29
        # The complete ordered oval avoids the straight forehead/temple corners.
        contour = (contour-eye_center)*1.025+eye_center
        cv2.fillPoly(mask,[np.int32(contour)],255)
        weight = cv2.GaussianBlur(mask,(0,0),max(1,width*.025))[...,None]/255.
        rgb = pixels[...,:3].astype(np.float32)
        gray = rgb@np.array([.2126,.7152,.0722],np.float32)
        if mode=='npc':
            target = cv2.GaussianBlur(gray,(0,0),max(1,width*.07))[...,None]*.07+np.array([151,151,151])
        else:
            target = (rgb*.60+gray[...,None]*.40)*.91*np.array([.95,1.,1.06])
        pixels[...,:3] = np.uint8(np.clip(rgb*(1-weight)+target*weight,0,255))
        layer = Image.new('RGBA',canvas.size)
        draw = ImageDraw.Draw(layer)
        stroke = max(1,round(width*.007))
        for eye in EYES:
            c = p[list(eye)].mean(axis=0)
            if mode=='doomer':
                points = [tuple(c+axis*x*width+down*(.035+.025*(1-(x/.10)**2))*width)
                          for x in np.linspace(-.10,.10,25)]
                draw.line(points,fill=(44,33,49,65),width=stroke*2+1)
            else:
                # Flat ink-like eye ovals contrast with the retained photo identity.
                points = [tuple(c+axis*np.cos(t)*width*.035+down*np.sin(t)*width*.035)
                          for t in np.linspace(0,2*np.pi,40)]
                draw.polygon(points,fill=(24,26,25,245))
                if expression=='angry':
                    side = -1 if float((c-eye_center)@axis)<0 else 1
                    outer = c+axis*side*width*.09-down*width*.065
                    inner = c-axis*side*width*.07-down*width*.020
                    _round_line(draw,[outer,inner],max(3,round(width*.023)))

        if mode=='npc':
            ink_width = max(3,round(width*.023))
            # Both moods share the same thick straight mouth and angular hooked nose.
            c = (p[61]+p[291])/2
            _round_line(draw,[c-axis*width*.13,c+axis*width*.13],ink_width)
            facing = -1 if float((p[1]-eye_center)@axis)<-width*.025 else 1
            nose_bottom = p[2]+down*width*.015
            nose_top = p[168]-axis*facing*width*.025+down*width*.015
            nose_foot = nose_bottom-axis*facing*width*.14
            _round_line(draw,[nose_top,nose_bottom,nose_foot],ink_width)
        composite = Image.alpha_composite(Image.fromarray(pixels),layer)
        if mode=='doomer':
            from .dealwithit import _place
            span = max(1.,float(np.linalg.norm(p[263]-p[33])))
            facing_left = float((p[1]-eye_center)@axis)<-.03*span
            asset = _cigarette()
            anchor = (asset.shape[1]*.02,asset.shape[0]*.78)
            mouth = p[291]+down*width*.035
            if facing_left:
                asset = np.ascontiguousarray(asset[:,::-1])
                anchor = (asset.shape[1]-1-anchor[0],anchor[1])
                mouth = p[61]+down*width*.035
            _place(composite,asset,anchor,mouth,span*.90,axis)
        pixels = np.array(composite)
    return restore(Image.fromarray(pixels),image)
