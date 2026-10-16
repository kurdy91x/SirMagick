"""Translate a segmented head intact; extend only the neck and adjoining hair."""
import cv2
import numpy as np
from PIL import Image

from .chudthor import OVAL
from .images import MAX_PIXELS


def _foreground(image,p,width,shoulder,person_mask=None):
    center = (p[234]+p[454])/2
    left = max(0,int(center[0]-width*.93))
    right = min(image.shape[1],int(center[0]+width*.93))
    top = max(0,int(p[10,1]-width*.65))
    bottom = min(image.shape[0],int(shoulder+width*.12))
    if right-left<8 or bottom-top<8:
        raise ValueError('No visible neck region for Giraffe.')
    if person_mask is not None:
        full = cv2.resize(person_mask,(image.shape[1],image.shape[0]),interpolation=cv2.INTER_LINEAR)
        roi = image[top:bottom,left:right,:3].copy()
        confidence = full[top:bottom,left:right]
        scale = min(1.,600/max(roi.shape[:2]))
        size = (max(8,round(roi.shape[1]*scale)),max(8,round(roi.shape[0]*scale)))
        small = cv2.resize(roi,size)
        confidence = cv2.resize(confidence,size)
        labels = np.where(confidence>128,cv2.GC_PR_FGD,cv2.GC_PR_BGD).astype(np.uint8)
        labels[confidence<8] = cv2.GC_BGD
        interior = cv2.erode(np.uint8(confidence>245),np.ones((5,5),np.uint8))
        labels[interior>0] = cv2.GC_FGD
        q = (p-[left,top])*scale
        cv2.fillConvexPoly(labels,cv2.convexHull(np.int32(q[list(OVAL)])),cv2.GC_FGD)
        if np.any(labels==cv2.GC_BGD):
            cv2.grabCut(small,labels,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),
                        3,cv2.GC_INIT_WITH_MASK)
        mask = np.uint8((labels==cv2.GC_FGD)|(labels==cv2.GC_PR_FGD))*255
        return (left,top,right,bottom),cv2.resize(mask,(right-left,bottom-top))
    roi = image[top:bottom,left:right,:3].copy()
    scale = min(1.,600/max(roi.shape[:2]))
    size = (max(8,round(roi.shape[1]*scale)),max(8,round(roi.shape[0]*scale)))
    small = cv2.resize(roi,size)
    q = (p-[left,top])*scale
    fw = width*scale
    yy,xx = np.mgrid[:size[1],:size[0]]
    cx = float((q[234,0]+q[454,0])/2)
    head = ((xx-cx)/(fw*.64))**2+((yy-q[10,1]-fw*.24)/(fw*.78))**2<1
    hair = (np.abs(xx-cx)<fw*.65)&(yy>q[10,1])&(yy<(shoulder-top)*scale)
    labels = np.full(yy.shape,cv2.GC_BGD,np.uint8)
    labels[head|hair] = cv2.GC_PR_FGD
    cv2.fillConvexPoly(labels,cv2.convexHull(np.int32(q[list(OVAL)])),cv2.GC_FGD)
    neck_x = float(q[152,0])
    cv2.rectangle(labels,(int(neck_x-fw*.10),int(q[152,1]+fw*.10)),
                  (int(neck_x+fw*.10),min(size[1]-3,int((shoulder-top)*scale-fw*.15))),cv2.GC_FGD,-1)
    labels[:2] = labels[-2:] = cv2.GC_BGD
    labels[:,:2] = labels[:,-2:] = cv2.GC_BGD
    cv2.grabCut(small,labels,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),
                3,cv2.GC_INIT_WITH_MASK)
    mask = np.uint8((labels==cv2.GC_FGD)|(labels==cv2.GC_PR_FGD))*255
    _, components = cv2.connectedComponents(mask)
    nose = np.int32(q[1]);nose[0]=np.clip(nose[0],0,size[0]-1);nose[1]=np.clip(nose[1],0,size[1]-1)
    component = components[nose[1],nose[0]]
    if component:mask[components!=component]=0
    mask = cv2.resize(mask,(right-left,bottom-top),interpolation=cv2.INTER_LINEAR)
    return (left,top,right,bottom),mask


def _shift_up(pixels,distance):
    """Integer translation: no resampling, scaling, or geometric deformation."""
    result = np.zeros_like(pixels)
    if 0<distance<len(pixels):result[:-distance]=pixels[distance:]
    elif distance==0:result[:]=pixels
    return result


def _select_strip(rgb,alpha,start,stop,thickness):
    """Find adjacent foreground rows with similar color and silhouette."""
    start = max(0,min(start,stop-thickness))
    best,score = start,float('inf')
    for row in range(start,max(start+1,stop-thickness+1)):
        colors = rgb[row:row+thickness].astype(np.float32)
        weights = np.minimum(alpha[row:row+thickness-1],alpha[row+1:row+thickness])
        amount = max(1.,float(weights.sum()))
        difference = np.abs(np.diff(colors,axis=0)).mean(axis=2)
        stability = float((difference*weights).sum())/amount
        boundary = float(np.abs(np.diff(alpha[row:row+thickness],axis=0)).mean())*80
        if stability+boundary<score:
            score = stability+boundary
            best = row
    return best


def _repeat_band(band,split,thickness,growth):
    """Insert copies without resampling any original image row."""
    frame = band[split:split+thickness]
    if not len(frame):return band.copy()
    repeated = frame[np.arange(growth)%len(frame)].copy()
    # Blend only the joins to the neighboring original rows, not the whole neck.
    join = min(max(1,len(frame)),growth//2)
    if join:
        t = np.linspace(0,1,join,dtype=np.float32)[:,None,None]
        previous = band[max(0,split-1):max(0,split-1)+1]
        following = band[split:split+1]
        repeated[:join] = previous*(1-t)+repeated[:join]*t
        repeated[-join:] = repeated[-join:]*(1-t)+following*t
    return np.concatenate((band[:split],repeated,band[split:]),axis=0)


def _scale_band(band,growth):
    """Extend premultiplied foreground vertically; preserve its horizontal scale."""
    return cv2.resize(band,(band.shape[1],len(band)+growth),interpolation=cv2.INTER_LINEAR)


def apply_effect(image,detection):
    detection.require('face')
    original = np.array(image.convert('RGBA'))
    people = []
    padding = 0
    for face in detection.faces:
        p = np.array([(point.x,point.y) for point in face],np.float32)
        width = max(8.,float(np.linalg.norm(p[454]-p[234])))
        chin = float(p[152,1])
        shoulder = min(image.height-2,chin+width*.65)
        for pose in detection.poses:
            if min(pose[11].visibility,pose[12].visibility)<.5:continue
            mid = np.array([(pose[11].x+pose[12].x)/2,(pose[11].y+pose[12].y)/2])
            if mid[1]>chin+width*.22 and abs(mid[0]-p[152,0])<width:
                shoulder = min(shoulder,float(mid[1]))
        cut = int(chin+width*.13)
        end = int(min(shoulder-width*.10,cut+width*.24))
        if end-cut<4:continue
        box,mask = _foreground(original,p,width,shoulder,detection.person_mask)
        rows = np.nonzero(mask>200)[0]
        if not len(rows):continue
        growth = max(1,round(width*.30))
        padding = max(padding,max(0,growth-(box[1]+int(rows.min()))+4))
        people.append((box,mask,cut,end,growth,width,p))
    if not people:raise ValueError('Giraffe needs a visible neck below the face.')
    if image.width*(image.height+padding)>MAX_PIXELS:
        raise ValueError('The giraffe result would exceed 24 million pixels.')
    result = cv2.copyMakeBorder(original,padding,0,0,0,cv2.BORDER_REPLICATE)
    for box,mask,cut,end,growth,width,p in people:
        left,top,right,bottom = box
        source = original[top:bottom,left:right]
        # Process only this person's crop; background pixels outside it stay exact.
        dest_top = max(0,top+padding-growth)
        dest_bottom = bottom+padding
        height = dest_bottom-dest_top
        offset = top+padding-dest_top
        foreground = np.zeros((height,right-left,4),np.float32)
        alpha = cv2.GaussianBlur(mask,(0,0),max(.6,width*.003))/255.
        alpha *= source[...,3]/255.
        head = np.zeros_like(foreground)
        # A horizontal cut below the chin keeps the whole head rigid and avoids
        # lifting either shoulder along a curved jaw boundary.
        cuts = np.full(right-left,cut,dtype=np.float32)
        rows = np.arange(len(source))+top
        head_alpha = alpha*np.clip((cuts[None]-rows[:,None])/max(1,width*.008),0,1)
        head[offset:offset+len(source),:,:3] = source[...,:3]*head_alpha[...,None]
        head[offset:offset+len(source),:,3] = head_alpha
        head[max(0,cut+padding-dest_top):] = 0
        head = _shift_up(head,growth)
        # Scale only the short neck/side-hair band, never the head or torso.
        # Columns which enter the person mask below the cut belong to shoulders
        # or clothing; they must not be pulled upward with the neck.
        overlap = max(2,round(width*.015))
        start = max(0,cut-top-overlap)
        stop = min(len(source),end-top)
        band_alpha = np.minimum.accumulate(alpha[start:stop],axis=0)
        band_alpha[:,alpha[start]<.5] = 0
        band = np.zeros((stop-start,right-left,4),np.float32)
        band[...,:3] = source[start:stop,:,:3]*band_alpha[...,None]
        band[...,3] = band_alpha
        expanded = _scale_band(band,growth)
        # A short lower overlap joins the fixed body without moving its pixels.
        blend = min(len(band),max(2,round(width*.035)))
        t = np.linspace(0,1,blend,dtype=np.float32)
        expanded[-blend:] *= (1-t*t*(3-2*t))[:,None,None]
        band_y = start+top+padding-growth-dest_top
        foreground[band_y:band_y+len(expanded)] = expanded
        a = head[...,3:4]
        foreground[...,:3] = head[...,:3]+foreground[...,:3]*(1-a)
        foreground[...,3:4] = a+foreground[...,3:4]*(1-a)
        old_mask = np.zeros((height,right-left),np.uint8)
        old_mask[offset:offset+len(source)] = np.uint8(head_alpha*255)
        holes = cv2.dilate(np.uint8(old_mask>3)*255,np.ones((3,3),np.uint8))
        holes[max(0,cut+padding-dest_top):] = 0
        base = result[dest_top:dest_bottom,left:right].copy()
        if np.any(holes):
            base[...,:3] = cv2.inpaint(base[...,:3].copy(),holes,max(2,int(width*.02)),cv2.INPAINT_TELEA)
        opacity = foreground[...,3:4]
        base[...,:3] = np.uint8(np.clip(foreground[...,:3]+base[...,:3]*(1-opacity),0,255))
        base[...,3:4] = np.uint8(np.clip(opacity*255+base[...,3:4]*(1-opacity),0,255))
        result[dest_top:dest_bottom,left:right] = base
    return Image.fromarray(result)
