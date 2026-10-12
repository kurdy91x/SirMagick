"""Face-local censorship, bloodshot eyes, laser eyes, and procedural fire."""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .chudthor import OVAL
from .warpface import EYES,MOUTH
from .effect_canvas import working,restore,points_for

MODES = ('censorface','censorbar','redeyes','lasereyes','firebreath','hellface')


def _glow(layer,radius):
    return Image.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius)),layer)


def apply_effect(image,detection,mode):
    if mode not in MODES:
        raise ValueError('Unknown face mask effect.')
    detection.require('face')
    if mode == 'hellface':
        return apply_effect(apply_effect(image,detection,'firebreath'),detection,'lasereyes')
    canvas = working(image)
    pixels = np.array(canvas)
    layer = Image.new('RGBA',canvas.size)
    draw = ImageDraw.Draw(layer)
    rng = np.random.default_rng(182)
    for face in detection.faces:
        p = points_for(face,canvas,image)
        axis = p[263]-p[33]
        span = max(3.,float(np.linalg.norm(axis)))
        axis /= span
        down = np.array([-axis[1],axis[0]])
        oval = p[list(OVAL)]
        fw = max(10.,float(np.ptp(oval@axis)))
        if mode == 'censorface':
            x0,y0 = np.maximum(0,np.floor(oval.min(axis=0)-fw*.10)).astype(int)
            x1,y1 = np.minimum(canvas.size,np.ceil(oval.max(axis=0)+fw*.10)).astype(int)
            if x0>=x1 or y0>=y1:
                continue
            roi = pixels[y0:y1,x0:x1,:3].astype(np.float32)
            blurred = cv2.GaussianBlur(roi,(0,0),max(3,fw*.075))
            grain = rng.normal(0,2.4,roi.shape[:2])[...,None]
            frosted = np.clip(blurred*.78+42+grain,0,255)
            mask = np.zeros(roi.shape[:2],np.uint8)
            center = oval.mean(axis=0)
            polygon = (oval-center)*1.08+center-[x0,y0]
            cv2.fillConvexPoly(mask,cv2.convexHull(np.int32(polygon)),255)
            weight = cv2.GaussianBlur(mask,(0,0),max(1,fw*.025))[...,None]/255
            pixels[y0:y1,x0:x1,:3] = np.uint8(roi*(1-weight)+frosted*weight)
        elif mode == 'censorbar':
            eyes = np.vstack([p[list(eye)] for eye in EYES])
            u,v = eyes@axis,eyes@down
            low,high = np.array([u.min()-fw*.08,v.min()-fw*.035]),np.array([u.max()+fw*.08,v.max()+fw*.035])
            corners = [axis*x+down*y for x,y in ((low[0],low[1]),(high[0],low[1]),(high[0],high[1]),(low[0],high[1]))]
            draw.polygon([tuple(c) for c in corners],fill=(0,0,0,255))
        elif mode == 'redeyes':
            for eye_index,eye in enumerate(EYES):
                contour = p[list(eye)]
                low = np.maximum(0,np.floor(contour.min(axis=0)-2)).astype(int)
                high = np.minimum(canvas.size,np.ceil(contour.max(axis=0)+3)).astype(int)
                x0,y0 = low; x1,y1 = high
                if x0>=x1 or y0>=y1:
                    continue
                mask = np.zeros((y1-y0,x1-x0),np.uint8)
                cv2.fillConvexPoly(mask,cv2.convexHull(np.int32(contour-low)),255)
                center = p[468+eye_index*5] if len(p)>=478 else contour.mean(axis=0)
                radius = max(1.,float(np.ptp(contour@axis))*.18)
                cv2.circle(mask,tuple(np.int32(center-low)),round(radius),0,-1)
                roi = pixels[y0:y1,x0:x1,:3].astype(np.float32)
                # Restrict tint to brighter sclera, keeping dark iris/lashes intact.
                white = np.clip((roi.mean(axis=-1)-30)/70,0,1)*mask/255
                veins = np.zeros(mask.shape,np.uint8)
                for _ in range(9):
                    x = int(rng.integers(0,max(1,x1-x0)))
                    y = int(rng.integers(0,max(1,y1-y0)))
                    cv2.line(veins,(x,y),(int(x+(x1-x0)*.15),int(y+rng.uniform(-2,2))),255,1,cv2.LINE_AA)
                amount = white*(.65+.30*veins/255)
                pixels[y0:y1,x0:x1,:3] = np.uint8(roi*(1-amount[...,None])+np.array([240,35,42])*amount[...,None])
        elif mode == 'lasereyes':
            center = (p[33]+p[263])/2
            side = -1 if (p[1]-center)@axis < -.02*span else 1
            bloom = Image.new('RGBA',canvas.size)
            glow_draw = ImageDraw.Draw(bloom)
            for eye in EYES:
                origin = p[list(eye)].mean(axis=0)
                direction = axis*side-down*.10
                direction /= np.linalg.norm(direction)
                normal = np.array([-direction[1],direction[0]])
                target = origin+direction*max(canvas.size)*1.4
                width = max(.7,fw*.007)
                for scale,color in ((10,(255,4,15,95)),(4,(255,12,24,170)),(1,(255,248,240,255))):
                    half = width*scale
                    polygon = [origin-normal*half,origin+normal*half,target+normal*half*.35,target-normal*half*.35]
                    painter = draw if scale==1 else glow_draw
                    painter.polygon([tuple(point) for point in polygon],fill=color)
                r = max(2.,fw*.025)
                glow_draw.ellipse((origin[0]-r*3,origin[1]-r*3,origin[0]+r*3,origin[1]+r*3),fill=(255,0,12,150))
                draw.ellipse((origin[0]-r*.6,origin[1]-r*.6,origin[0]+r*.6,origin[1]+r*.6),fill=(255,250,235,255))
                for ray,length in ((axis,fw*.11),(down,fw*.065)):
                    draw.line((*tuple(origin-ray*length),*tuple(origin+ray*length)),fill=(255,130,130,190),width=1)
            layer = Image.alpha_composite(bloom.filter(ImageFilter.GaussianBlur(max(1.,fw*.016))),layer)
            draw = ImageDraw.Draw(layer)
        else:
            mouth = p[list(MOUTH)].mean(axis=0)
            center = (p[33]+p[263])/2
            side = -1 if (p[1]-center)@axis < -.02*span else 1
            direction = axis*side-down*.16
            angle = -np.degrees(np.arctan2(direction[1],direction[0]))
            yy,xx = np.mgrid[:180,:420].astype(np.float32)
            u,v = xx/419,(yy-90)/90
            radius = .07+.70*u**.7
            wobble = .12*np.sin(u*26)+.06*np.sin(u*65+v*4)
            fire = np.clip((1-np.abs(v-wobble)/radius)*3,0,1)*np.clip((1-u)*4,0,1)
            core = np.clip(1-np.abs(v-wobble)/radius,0,1)
            flame = np.zeros((180,420,4),np.uint8)
            flame[...,0] = 255
            flame[...,1] = np.uint8(50+205*core**1.2)
            flame[...,2] = np.uint8(12+170*core**4)
            flame[...,3] = np.uint8(fire*245)
            sprite = Image.fromarray(flame).resize((max(8,round(fw*1.5)),max(4,round(fw*.65))),Image.Resampling.LANCZOS)
            origin = np.array([0,sprite.height/2])
            turned = sprite.rotate(angle,Image.Resampling.BICUBIC,expand=True)
            delta = origin-np.array(sprite.size)/2
            perpendicular = np.array([-direction[1],direction[0]])
            direction /= np.linalg.norm(direction)
            perpendicular /= np.linalg.norm(perpendicular)
            anchor = direction*delta[0]+perpendicular*delta[1]+np.array(turned.size)/2
            layer.alpha_composite(turned,tuple(np.int32(mouth-anchor)))
    canvas = Image.fromarray(pixels)
    if mode in ('lasereyes','firebreath'):
        layer = _glow(layer,max(2,min(canvas.size)*.009))
    canvas = Image.alpha_composite(canvas,layer)
    return restore(canvas,image)
