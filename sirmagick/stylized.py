"""Prism light leaks and refracted photo highlights."""
import secrets

import cv2
import numpy as np
from PIL import Image,ImageEnhance,ImageFilter

from .effect_canvas import working,restore

MODES = ('prismglow',)


def apply_effect(image,mode,seed=None):
    if mode not in MODES:
        raise ValueError('Unknown stylization.')
    canvas = working(image,1200)
    rgb = np.asarray(canvas)[...,:3].copy()
    alpha = np.asarray(canvas)[...,3:4]/255
    rgb = np.uint8(rgb*alpha)
    h,w = rgb.shape[:2]
    rng = np.random.default_rng(secrets.randbits(64) if seed is None else seed)
    saturated = np.asarray(ImageEnhance.Color(Image.fromarray(rgb)).enhance(1.7),np.float32)/255
    yy,xx = np.mgrid[:h,:w].astype(np.float32)
    x,y = xx/max(1,w-1),yy/max(1,h-1)
    light = saturated @ np.array([.2126,.7152,.0722],np.float32)
    grade = np.array([1.15,.98,.83])*saturated
    grade += (1-light)[...,None]*np.array([0,.07,.11])
    bloom = cv2.GaussianBlur(np.clip(grade-.65,0,1),(0,0),max(1,min(w,h)*.018))
    output = grade+bloom*.8
    edge = np.clip(np.abs(x-.5)*2,0,1)
    # Local soft double exposures imitate refracting glass, leaving the center clear.
    for offset,side in ((.065,1),(-.045,-1)):
        mx = np.float32(xx+offset*w+.015*w*np.sin(y*15))
        my = np.float32(yy+.02*h*np.sin(x*12))
        echo = cv2.remap(saturated,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
        strength = edge*.24*np.clip((x-.5)*side*3,0,1)
        output = output*(1-strength[...,None])+echo*strength[...,None]
    for index in range(15):
        cx = float(rng.uniform(-.1,.22) if index%2 else rng.uniform(.78,1.1))
        cy = float(rng.uniform(-.1,1.1))
        radius = float(rng.uniform(.025,.13))
        distance = np.hypot((x-cx)*w/min(w,h),(y-cy)*h/min(w,h))
        disc = np.clip((radius-distance)/max(.004,radius*.22),0,1)*.22
        ring = np.exp(-((distance-radius)/(radius*.10+.002))**2)*.12
        color = np.array([1.,.45,.08]) if index%2 else np.array([.05,.8,1.])
        output += color*(disc+ring)[...,None]
    warm = np.exp(-((x-.98)/.19)**2)*(.4+.2*np.sin(y*6))
    cool = np.exp(-((x-.02)/.15)**2)*.30
    output += warm[...,None]*np.array([.7,.15,.01])+cool[...,None]*np.array([.02,.4,.5])
    result = Image.fromarray(np.uint8(np.clip(output*255,0,255))).convert('RGBA')
    return restore(result,image)
