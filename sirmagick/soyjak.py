"""Photo-based surprised Wojak expression with landmark-aligned ink accents."""
import cv2
import numpy as np
from PIL import Image, ImageDraw

from .chudthor import OVAL
from .warpface import EYES, MOUTH
from .effect_canvas import working, restore, points_for


def apply_effect(image, detection):
    from .face_transformers import warp_region
    detection.require('face')
    canvas = working(image, 1200)
    pixels = np.array(canvas)
    layer = Image.new('RGBA', canvas.size)
    draw = ImageDraw.Draw(layer)
    rng = np.random.default_rng(371)
    for face in detection.faces:
        p = points_for(face, canvas, image)
        axis = p[263]-p[33]
        axis /= max(1., float(np.linalg.norm(axis)))
        down = np.array([-axis[1], axis[0]], np.float32)
        width = max(8., float(np.ptp(p[list(OVAL)]@axis)))
        warp_region(pixels,p[[172,136,150,149,176,148,152,377,400,378,379,365,397]],.84,.80,
                    shift=(0,-width*.025),axis=axis)
        for eye in EYES:
            warp_region(pixels,p[list(eye)],1.30,1.85,axis=axis,padding=(1.2,1.8))
        warp_region(pixels,p[list(MOUTH)],1.20,2.7,axis=axis,padding=(1.25,1.7))
        center = (p[61]+p[291])/2+down*width*.025
        mouth_width = max(width*.135,float(np.linalg.norm(p[291]-p[61]))*.53)
        mouth_height = width*.165
        def xy(u,v):
            return tuple(center+axis*u+down*v)
        # Mouth cavity with a rounded silhouette and a restrained lip rim.
        angles = np.linspace(0,2*np.pi,90)
        def oval(rx,ry,offset=0):
            return [xy(np.cos(t)*rx,np.sin(t)*ry+offset) for t in angles]
        draw.polygon(oval(mouth_width*1.09,mouth_height*1.07),fill=(75,35,32,200))
        draw.polygon(oval(mouth_width,mouth_height),fill=(24,13,16,255))
        # Individual upper teeth follow the cavity rather than a rectangular strip.
        for index in range(6):
            left = (-.87+index*.29)*mouth_width
            right = left+mouth_width*.275
            top = -mouth_height*np.sqrt(max(.02,1-(left/mouth_width)**2))
            right_top = -mouth_height*np.sqrt(max(.02,1-(right/mouth_width)**2))
            bottom = -mouth_height*.40+abs(index-2.5)*mouth_height*.035
            draw.polygon([xy(left,top+2),xy(right,right_top+2),xy(right,bottom),xy(left,bottom)],
                         fill=(218+index%2*9,209+index%2*9,187+index%2*9,255))
        tongue = [xy(np.cos(t)*mouth_width*.66,
                     mouth_height*.72+np.sin(t)*mouth_height*.18) for t in angles]
        draw.polygon(tongue,fill=(106,47,55,255))
        stroke = max(1,round(width*.006))
        # Ink creases under the eyes and short beard strokes near the jaw.
        for eye in EYES:
            c = p[list(eye)].mean(axis=0)
            curve = [tuple(c+axis*x*width+down*(.045+.013*(1-(x/.10)**2))*width)
                     for x in np.linspace(-.10,.10,20)]
            draw.line(curve,fill=(40,31,27,125),width=stroke+1)
        for _ in range(170):
            u,v = rng.uniform(-.36,.36),rng.uniform(.07,.35)
            if (u/.38)**2+((v-.12)/.30)**2>1 or abs(u)<.21 and v<.23:
                continue
            start = center+axis*u*width+down*v*width
            end = start+down*width*.014+axis*rng.uniform(-.004,.004)*width
            draw.line([tuple(start),tuple(end)],fill=(32,27,24,105),width=max(1,stroke//2))
    return restore(Image.alpha_composite(Image.fromarray(pixels),layer),image)
