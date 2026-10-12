"""Local CPU face and body remaps with smoothly blended spatial falloffs."""
import cv2
import numpy as np
from PIL import Image

from .chudthor import OVAL
from .warpface import EYES, MOUTH, NOSE
from .effect_canvas import working,restore,points_for

MODES = ('alienface','longface','goblin','giga','meltface','fatmagic')


def warp_region(pixels,points,sx=1.,sy=1.,shift=(0.,0.),axis=None,padding=(1.,1.),vertical_limits=None):
    points = np.asarray(points,np.float32)
    axis = np.array([1.,0.],np.float32) if axis is None else axis
    down = np.array([-axis[1],axis[0]],np.float32)
    coords = np.column_stack((points@axis,points@down))
    center_uv = (coords.min(axis=0)+coords.max(axis=0))/2
    center = axis*center_uv[0]+down*center_uv[1]
    radii = np.maximum(3,np.ptp(coords,axis=0)/2*np.array(padding))
    reach = radii*np.maximum([sx,sy],1)*2.1+np.abs(shift)
    box = np.abs(axis)*reach[0]+np.abs(down)*reach[1]
    h,w = pixels.shape[:2]
    x0,y0 = np.maximum(0,np.floor(center-box)).astype(int)
    x1,y1 = np.minimum([w,h],np.ceil(center+box+1)).astype(int)
    if x0>=x1 or y0>=y1:
        return
    yy,xx = np.mgrid[y0:y1,x0:x1].astype(np.float32)
    dx,dy = xx-center[0],yy-center[1]
    u,v = dx*axis[0]+dy*axis[1],dx*down[0]+dy*down[1]
    r = np.hypot(u/(radii[0]*max(1,sx)),v/(radii[1]*max(1,sy)))
    t = np.clip(r-1,0,1)
    weight = 1-t*t*(3-2*t)
    if vertical_limits is not None:
        top,bottom = vertical_limits
        fade = max(3.,(bottom-top)*.18)
        a = np.clip((yy-top)/fade,0,1)
        b = np.clip((bottom+fade-yy)/fade,0,1)
        weight *= a*a*(3-2*a)*b*b*(3-2*b)
    a = (u-shift[0]*weight)/(1+(sx-1)*weight)
    b = (v-shift[1]*weight)/(1+(sy-1)*weight)
    mx = np.float32(center[0]+a*axis[0]+b*down[0])
    my = np.float32(center[1]+a*axis[1]+b*down[1])
    # Premultiplied sampling prevents hidden colors entering the face texture.
    source = pixels.astype(np.float32)
    source[...,:3] *= source[...,3:4]/255
    sample = cv2.remap(source,mx,my,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
    np.divide(sample[...,:3]*255,sample[...,3:4],out=sample[...,:3],where=sample[...,3:4]>0)
    active = weight>1e-5
    pixels[y0:y1,x0:x1][active] = np.uint8(np.clip(sample[active],0,255))


def apply_effect(image,detection,mode):
    if mode not in MODES:
        raise ValueError('Unknown face transformer.')
    detection.require('face')
    canvas = working(image)
    pixels = np.array(canvas)
    if mode == 'fatmagic':
        for pose in detection.poses:
            if all(pose[i].visibility>.5 for i in (11,12,23,24)):
                points = points_for(pose,canvas,image)
                torso = points[[11,12,23,24]]
                # Keep body deformation below the shoulders so nearby heads survive.
                top = float(min(points[11,1],points[12,1]))
                bottom = float(max(points[23,1],points[24,1]))
                # Broad, smooth horizontal expansion; never squash the torso vertically.
                # The original elliptical core produced abrupt horizontal ridges.
                yy,xx = np.mgrid[:pixels.shape[0],:pixels.shape[1]].astype(np.float32)
                fraction = np.clip((yy-top)/max(1.,bottom-top),0,1)
                shoulder = (points[11]+points[12])/2
                hip = (points[23]+points[24])/2
                center = shoulder[0]*(1-fraction)+hip[0]*fraction
                radius = max(8.,float(np.ptp(torso[:,0]))*.9)
                height = max(8.,bottom-top)
                vertical = np.sin(np.pi*np.clip((yy-top)/(height*1.5),0,1))**2
                horizontal = np.exp(-((xx-center)/radius)**2)
                mx = np.float32(center+(xx-center)/(1+.66*vertical*horizontal))
                warped = cv2.remap(pixels,mx,yy,cv2.INTER_LINEAR,borderMode=cv2.BORDER_REPLICATE)
                active = (vertical*horizontal)>1e-5
                pixels[active] = warped[active]
    for face in detection.faces:
        p = points_for(face,canvas,image)
        axis = p[263]-p[33]
        axis /= max(1.,float(np.linalg.norm(axis)))
        oval = p[list(OVAL)]
        width = max(5.,float(np.ptp(oval@axis)))
        if mode in ('longface','alienface'):
            if mode == 'alienface':
                for eye in EYES:
                    warp_region(pixels,p[list(eye)],1.65,1.8,axis=axis,padding=(1.15,1.8))
                for indices in (NOSE,MOUTH):
                    warp_region(pixels,p[list(indices)],.65,.7,axis=axis)
                mask = np.zeros(pixels.shape[:2],np.uint8)
                cv2.fillConvexPoly(mask,cv2.convexHull(np.int32(oval)),255)
                mask = cv2.GaussianBlur(mask,(0,0),max(1,width*.035))/255
                gray = pixels[...,:3].astype(np.float32)@np.array([.2126,.7152,.0722])
                gray_rgb = gray[...,None]*np.array([.83,.94,.92])+12
                pixels[...,:3] = np.uint8(np.clip(pixels[...,:3]*(1-mask[...,None])+gray_rgb*mask[...,None],0,255))
                for eye in EYES:
                    eye_points = p[list(eye)]
                    center = eye_points.mean(axis=0)
                    eye_points = (eye_points-center)*[1.6,2.1]+center
                    eye_mask = np.zeros(pixels.shape[:2],np.uint8)
                    cv2.fillConvexPoly(eye_mask,cv2.convexHull(np.int32(eye_points)),255)
                    eye_mask = cv2.GaussianBlur(eye_mask,(0,0),max(.6,width*.006))/255
                    pixels[...,:3] = np.uint8(pixels[...,:3]*(1-eye_mask[...,None]*.88))
            warp_region(pixels,oval,.8,1.48,axis=axis)
        elif mode == 'goblin':
            warp_region(pixels,p[list(NOSE)],1.8,1.55,axis=axis,padding=(1.4,1.1))
            warp_region(pixels,p[list(MOUTH)],1.5,1.1,axis=axis)
            for eye in EYES:
                warp_region(pixels,p[list(eye)],.72,.8,axis=axis,padding=(1.3,1.6))
            for temple in ((127,234,93),(356,454,323)):
                warp_region(pixels,p[list(temple)],1.4,1.05,axis=axis,padding=(2.,1.3))
        elif mode == 'giga':
            warp_region(pixels,p[[234,93,132,58,172,152,397,288,361,323,454]],1.48,1.08,axis=axis)
            warp_region(pixels,p[[172,136,150,149,176,148,152,377,400,378,379,365,397]],1.25,1.25,axis=axis)
        elif mode == 'meltface':
            for indices,distance in ((*[(eye,.11) for eye in EYES],(NOSE,.16),(MOUTH,.22))):
                warp_region(pixels,p[list(indices)],.98,1.32,shift=(0,width*distance),axis=axis,padding=(1.25,1.7))
        else:
            warp_region(pixels,oval,1.18,1.,axis=axis)
    return restore(Image.fromarray(pixels),image)
