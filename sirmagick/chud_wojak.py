"""Angular photo Chud Wojak with rectangular glasses and exaggerated closed lips."""
import cv2
import numpy as np
from PIL import Image, ImageDraw

from .chudthor import OVAL
from .warpface import EYES, MOUTH, NOSE
from .effect_canvas import working, restore, points_for


def transformed_points(points,region,sx,sy,axis,padding):
    """Invert the same destination-to-source map used by warp_region."""
    down = np.array([-axis[1],axis[0]],np.float32)
    basis = np.column_stack((axis,down))
    bounds = np.asarray(region)@basis
    center = (bounds.min(axis=0)+bounds.max(axis=0))/2
    radii = np.maximum(3,np.ptp(bounds,axis=0)/2*np.array(padding))
    source = np.asarray(points)@basis-center
    scale = np.array([sx,sy])
    target = source*scale
    for _ in range(40):
        r = np.linalg.norm(target/(radii*np.maximum(scale,1)),axis=1)
        t = np.clip(r-1,0,1)
        weight = 1-t*t*(3-2*t)
        estimate = source*(1+(scale-1)*weight[:,None])
        target = (target+estimate)/2
    return np.float32((target+center)@basis.T)


def _clean_ink(pixels,p,width):
    """Remove sparse dark line components in glasses/lip areas before another pass."""
    zone = np.zeros(pixels.shape[:2],np.uint8)
    for indices,margin in ((tuple(i for eye in EYES for i in eye),.14),(MOUTH,.10)):
        points = p[list(indices)]
        lo = np.maximum(0,np.floor(points.min(axis=0)-width*margin)).astype(int)
        hi = np.minimum([pixels.shape[1]-1,pixels.shape[0]-1],np.ceil(points.max(axis=0)+width*margin)).astype(int)
        cv2.rectangle(zone,tuple(lo),tuple(hi),255,-1)
    dark = np.uint8((pixels[...,:3].max(axis=-1)<85)&(zone>0))
    count,labels,stats,_ = cv2.connectedComponentsWithStats(dark)
    erase = np.zeros(zone.shape,np.uint8)
    for index in range(1,count):
        x,y,w,h,area = stats[index]
        density = area/max(1,w*h)
        if max(w,h)>width*.10 and .0006*width*width<area<.10*width*width and density<.42:
            erase[labels==index] = 255
    if not np.any(erase):
        return
    erase = cv2.dilate(erase,np.ones((3,3),np.uint8))
    for index in (468,473):
        if index<len(p):
            cv2.circle(erase,tuple(np.int32(p[index])),max(1,round(width*.018)),0,-1)
    pixels[...,:3] = cv2.inpaint(pixels[...,:3].copy(),erase,max(2,int(width*.012)),cv2.INPAINT_TELEA)


def apply_effect(image,detection):
    from .face_transformers import warp_region
    detection.require('face')
    canvas = working(image,1200)
    pixels = np.array(canvas)
    for face in detection.faces:
        p = points_for(face,canvas,image)
        axis = p[263]-p[33]
        axis /= max(1.,float(np.linalg.norm(axis)))
        down = np.array([-axis[1],axis[0]],np.float32)
        oval = p[list(OVAL)]
        width = max(8.,float(np.ptp(oval@axis)))
        _clean_ink(pixels,p,width)
        def deform(indices,sx,sy,padding):
            nonlocal p
            region = p[list(indices)].copy()
            warp_region(pixels,region,sx,sy,axis=axis,padding=padding)
            p = transformed_points(p,region,sx,sy,axis,padding)
        for eye in EYES:
            deform(eye,.73,.63,(1.2,1.7))
        deform(NOSE,.94,1.22,(1.25,1.1))
        thickness = float(np.linalg.norm(p[17]-p[0]))/width
        mouth_scale = 1.65 if thickness<.075 else 1.10
        deform(MOUTH,1.22,mouth_scale,(.95,1.05))
        aspect = float(np.ptp(p[list(OVAL)]@down))/width
        head_scale = 1.06 if aspect<1.65 else 1.0
        deform(OVAL,.95 if aspect<1.65 else 1.,head_scale,(1.05,1.05))
        oval = p[list(OVAL)]
        width = max(8.,float(np.ptp(oval@axis)))
        mask = np.zeros(pixels.shape[:2],np.uint8)
        cv2.fillConvexPoly(mask,cv2.convexHull(np.int32(oval)),255)
        weight = cv2.GaussianBlur(mask,(0,0),max(1,width*.025))[...,None]/255.
        rgb = pixels[...,:3].astype(np.float32)
        gray = rgb@np.array([.2126,.7152,.0722],np.float32)
        pale = rgb*.45+gray[...,None]*.40+33
        pixels[...,:3] = np.uint8(np.clip(rgb*(1-weight)+pale*weight,0,255))
        layer = Image.new('RGBA',canvas.size)
        draw = ImageDraw.Draw(layer)
        stroke = max(1,round(width*.012))
        def line(points,thickness=stroke,alpha=220):
            draw.line([tuple(q) for q in points],fill=(20,18,17,alpha),width=thickness,joint='curve')
        centers = []
        inner_edges = []
        for index,indices in enumerate(EYES):
            eye = p[list(indices)]
            bounds = np.column_stack((eye@axis,eye@down))
            mid = (bounds.min(axis=0)+bounds.max(axis=0))/2
            c = axis*mid[0]+down*mid[1]
            centers.append(c)
            # Each lens gets its own perspective-dependent width and height.
            rx = max(width*.075,float(np.ptp(bounds[:,0]))*.85)
            ry = max(width*.043,float(np.ptp(bounds[:,1]))*.85)
            corners = [c+axis*x*rx+down*y*ry for x,y in ((-1,-1),(1,-1),(1,1),(-1,1),(-1,-1))]
            line(corners)
            side = -1 if index==0 else 1
            inner_edges.append(c-axis*side*rx)
            outer = c+axis*side*rx
            temple = p[127 if index==0 else 356]
            line([outer,temple-down*width*.065])
            brow_outer = p[70 if index==0 else 300]
            brow_inner = p[107 if index==0 else 336]
            line([brow_outer-down*width*.018,brow_inner+down*width*.01],stroke*2)
        bridge = p[168]+down*width*.012
        line([inner_edges[0],bridge,inner_edges[1]])
        mouth_axis = p[291]-p[61]
        mouth_axis /= max(1.,float(np.linalg.norm(mouth_axis)))
        mouth_down = np.array([-mouth_axis[1],mouth_axis[0]],np.float32)
        center = (p[13]+p[14])/2
        # Thick closed lips with a cupid's bow, protruding center, and a lower lip.
        lip_width = min(width*.20,max(width*.10,float(np.linalg.norm(p[291]-p[61]))*.52))
        lip_height = np.clip(float(np.linalg.norm(p[17]-p[0]))*.48,width*.028,width*.045)
        lip_width *= 1.30
        lip_height *= 1.30
        def lip(u,v):
            return center+mouth_axis*u*lip_width+mouth_down*(v/.06)*lip_height
        boundary = [lip(u,v) for u,v in ((-1,0),(-.66,-.038),(-.23,-.050),(0,-.023),
                                         (.24,-.048),(.70,-.032),(1,0),(.65,.055),
                                         (0,.075),(-.65,.045),(-1,0))]
        # Opaque lip-colored fill covers the original lips/teeth beneath the outline.
        samples = np.rint(p[[0,17]]).astype(int)
        samples[:,0] = np.clip(samples[:,0],0,pixels.shape[1]-1)
        samples[:,1] = np.clip(samples[:,1],0,pixels.shape[0]-1)
        color = np.uint8(np.clip(pixels[samples[:,1],samples[:,0],:3].mean(axis=0)*.93,0,255))
        draw.polygon([tuple(q) for q in boundary],fill=tuple(int(c) for c in color)+(255,))
        line(boundary,stroke,180)
        line([lip(-1,0),lip(-.45,.015),lip(0,.005),lip(.45,.018),lip(1,0)],stroke,220)
        brow = (centers[0]+centers[1])/2
        for side in (-1,1):
            line([brow+axis*side*width*.055-down*width*.12,
                  brow+axis*side*width*.065-down*width*.19,
                  brow+axis*side*width*.045-down*width*.25],max(1,stroke//2),160)
            cheek = p[234] if side<0 else p[454]
            line([cheek-axis*side*width*.06,cheek-axis*side*width*.08+down*width*.12],max(1,stroke//2),120)
        pixels = np.array(Image.alpha_composite(Image.fromarray(pixels),layer))
    return restore(Image.fromarray(pixels),image)
