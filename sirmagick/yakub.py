"""Segment and reshape the upper head without warping the background."""
import cv2
import numpy as np
from PIL import Image

from .chudthor import OVAL
from .effect_canvas import working, restore, points_for


def apply_effect(image, detection):
    detection.require('face')
    canvas = working(image, 1100)
    original = np.array(canvas)
    faces = [points_for(face, canvas, image) for face in detection.faces]
    widths = [max(8., float(np.linalg.norm(p[454]-p[234]))) for p in faces]
    padding = max(0, int(max(1.55*w-float(((p[33]+p[263])/2)[1]) for p,w in zip(faces,widths))))
    pixels = cv2.copyMakeBorder(original, padding, 0, 0, 0, cv2.BORDER_REPLICATE)
    yy, xx = np.mgrid[:pixels.shape[0], :pixels.shape[1]].astype(np.float32)
    for landmarks, width in zip(faces, widths):
        p = landmarks + [0, padding]
        axis = p[263]-p[33]
        axis /= max(1., float(np.linalg.norm(axis)))
        down = np.array([-axis[1], axis[0]], np.float32)
        origin = (p[33]+p[263])/2
        dx, dy = xx-origin[0], yy-origin[1]
        u = (dx*axis[0]+dy*axis[1])/width
        v = (dx*down[0]+dy*down[1])/width
        # Color-based segmentation seeded by the face and estimated scalp.
        extent = (u/.61)**2 + ((v+.25)/.82)**2
        labels = np.full(pixels.shape[:2], cv2.GC_BGD, np.uint8)
        labels[extent < 1] = cv2.GC_PR_FGD
        face = np.zeros(labels.shape, np.uint8)
        cv2.fillConvexPoly(face, cv2.convexHull(np.int32(p[list(OVAL)])), 1)
        labels[face > 0] = cv2.GC_FGD
        labels[(np.abs(u)<.19)&(v<-.12)&(v>-.48)] = cv2.GC_FGD
        labels[:padding] = cv2.GC_BGD
        cv2.grabCut(pixels[...,:3].copy(), labels, None,
                    np.zeros((1,65),np.float64), np.zeros((1,65),np.float64),
                    2, cv2.GC_INIT_WITH_MASK)
        mask = np.uint8((labels==cv2.GC_FGD)|(labels==cv2.GC_PR_FGD))*255
        # Keep only the connected component containing the detected face.
        _, components = cv2.connectedComponents(mask)
        cy, cx = np.int32(p[1])[::-1]
        component = components[np.clip(cy,0,mask.shape[0]-1),np.clip(cx,0,mask.shape[1]-1)]
        if component:
            mask[components!=component] = 0
        mask[v>.38] = 0
        feather = cv2.GaussianBlur(mask,(0,0),max(.7,width*.008))/255.
        feather *= np.clip((.38-v)/.12,0,1)
        # Broad rounded paired lobes; narrow facial proportions below the brow.
        upper = np.clip(-v/.38,0,1)
        upper = upper*upper*(3-2*upper)
        stretch = 1+1.35*upper*np.exp(-((v+.85)/.63)**2)
        source_u = u/stretch
        source_v = np.where(v<0,v/1.85,v)
        source_v -= .12*np.exp(-(u/.20)**2)*np.exp(-((v+1.02)/.32)**2)
        mx = np.float32(origin[0]+width*(source_u*axis[0]+source_v*down[0]))
        my = np.float32(origin[1]+width*(source_u*axis[1]+source_v*down[1]))
        alpha = cv2.remap(np.float32(feather),mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        destination_fade = np.clip((.38-v)/.12,0,1)
        alpha *= destination_fade
        premult = pixels[...,:3].astype(np.float32)*feather[...,None]
        sampled = cv2.remap(premult,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_CONSTANT)
        sampled *= destination_fade[...,None]
        # Fill only the old upper-head footprint. The lower face stays connected.
        erase = np.uint8((mask>0)&(v<-.02))*255
        background = cv2.inpaint(pixels[...,:3].copy(),erase,max(3,int(width*.025)),cv2.INPAINT_TELEA)
        pixels[...,:3] = np.uint8(np.clip(background*(1-alpha[...,None])+sampled,0,255))
    return restore(Image.fromarray(pixels), image)
