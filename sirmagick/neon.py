"""Glowing Tron-style contour lighting."""
import cv2
import numpy as np
from PIL import Image

from .chudthor import OVAL

MODES = ('tron',)


def _geometry(detection, size, original_size):
    """Build facial exclusion masks and sparse landmark-aligned light segments."""
    w,h = size
    face_mask = np.zeros((h,w),np.uint8)
    lines = face_mask.copy()
    if detection is None:
        return face_mask, lines
    scale = np.array([w/original_size[0],h/original_size[1]])
    for face in detection.faces:
        points = np.array([(p.x,p.y) for p in face])*scale
        oval = points[list(OVAL)]
        extent = np.maximum(np.ptp(oval,axis=0),2)
        cv2.fillConvexPoly(face_mask,cv2.convexHull(np.int32(oval)),255)
        # Open, sparse segments avoid tracing wrinkles, shadows, and beard texture.
        paths = ((234,93,132,58,172), (397,365,379,378,400,377,152),
                 (70,63,105,66,107), (336,296,334,293,300),
                 (33,160,159,158,133), (362,385,386,387,263),
                 (61,40,37,0,267,270,291), (17,314,405,321))
        stroke = max(1,round(extent[0]*.006))
        for path in paths:
            curve = points[list(path)]
            # Densify with a cubic Hermite spline for smooth landmark-aligned lines.
            padded = np.vstack((curve[0],curve,curve[-1]))
            samples = []
            for i in range(1,len(padded)-2):
                a,b,c,d = padded[i-1:i+3]
                t = np.linspace(0,1,10)[:,None]
                samples.extend(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t))
            cv2.polylines(lines,[np.int32(samples)],False,255,stroke,cv2.LINE_AA)
    return face_mask,lines


def apply_effect(image, mode, detection=None):
    if mode not in MODES:
        raise ValueError('Unknown neon effect.')
    original = image.convert('RGBA')
    work = original.copy()
    work.thumbnail((1600,1600), Image.Resampling.LANCZOS)
    pixels = np.asarray(work)
    rgb = pixels[...,:3].astype(np.float32)/255*(pixels[...,3:4]/255)
    h,w = rgb.shape[:2]
    gray = rgb @ np.array([.2126,.7152,.0722],np.float32)
    face_mask,face_lines = _geometry(detection,(w,h),original.size)
    smooth = cv2.bilateralFilter(np.uint8(gray*255),9,65,65)
    smooth = cv2.GaussianBlur(smooth,(0,0),max(1.,min(w,h)*.002))
    raw = cv2.Canny(smooth,55,120)
    raw[face_mask>0] = 0
    edges = np.zeros_like(raw)
    contours,_ = cv2.findContours(raw,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)
    for contour in contours:
        if cv2.arcLength(contour,False) < max(8,min(w,h)*.10):
            continue
        simple = cv2.approxPolyDP(contour,max(.7,min(w,h)*.001),False)
        cv2.polylines(edges,[simple],False,150,1,cv2.LINE_AA)
    edges = np.maximum(edges,face_lines).astype(np.float32)/255
    glow = cv2.GaussianBlur(edges,(0,0),max(1.,min(w,h)*.004))
    base = rgb*.23+gray[...,None]*np.array([.01,.04,.07])
    colored = edges[...,None]*np.array([.12,.88,1.])
    colored += glow[...,None]*np.array([.05,.85,1.])*2.8
    # Bright contour cores with broad electric cyan bloom.
    output = base+colored
    result = Image.fromarray(np.uint8(np.clip(output*255,0,255)))
    if result.size != original.size:
        result = result.resize(original.size,Image.Resampling.LANCZOS)
    result = result.convert('RGBA')
    result.putalpha(original.getchannel('A'))
    return result
