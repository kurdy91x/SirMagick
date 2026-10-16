"""Controlled private proof using manually supplied regions on a plain background.

This is an experiment, not the production Giraffe effect or a generic segmenter.
The background fit is appropriate only for a smooth, unobstructed backdrop.
"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import cv2
import numpy as np
from PIL import Image,ImageDraw
from sirmagick.giraffe import _repeat_band
from sirmagick.images import load_image


def background_fit(rgb,mask,limit):
    h,w = rgb.shape[:2]
    yy,xx = np.mgrid[:limit:5,:w:5]
    x,y = xx.ravel()/w,yy.ravel()/h
    terms = np.column_stack((np.ones_like(x),x,y,x*x,x*y,y*y))
    colors = rgb[yy,xx].reshape(-1,3).astype(float)
    keep = mask[yy,xx].ravel()<.01
    for _ in range(3):
        coefficients = np.linalg.lstsq(terms[keep],colors[keep],rcond=None)[0]
        residual = np.linalg.norm(colors-terms@coefficients,axis=1)
        keep &= residual<max(6,float(np.median(residual[keep]))*4)
    return coefficients


def render(rgb,mask,config,growth,method,coefficients):
    h,w = rgb.shape[:2]
    cut,end = config['cut_y'],config['band_end']
    first_row = int(np.nonzero(mask>.5)[0].min())
    padding = max(0,growth-first_row+8)
    base = np.pad(rgb,((padding,0),(0,0),(0,0)),mode='edge').copy()
    # Reconstruct the smooth backdrop only where the old head was removed.
    yy,xx = np.mgrid[:cut+padding,:w]
    x,y = xx/w,(yy-padding)/h
    fitted = (coefficients[0]+x[...,None]*coefficients[1]+y[...,None]*coefficients[2]
              +(x*x)[...,None]*coefficients[3]+(x*y)[...,None]*coefficients[4]
              +(y*y)[...,None]*coefficients[5])
    erase = np.zeros(xx.shape,np.float32)
    erase[padding:] = mask[:cut]
    erase[:padding] = 1
    base[:cut+padding] = np.uint8(np.clip(base[:cut+padding]*(1-erase[...,None])+fitted*erase[...,None],0,255))
    alpha = mask[cut:end]
    band = np.zeros((end-cut,w,4),np.float32)
    band[...,:3] = rgb[cut:end]*alpha[...,None]
    band[...,3] = alpha
    if method=='repeat':
        expanded = _repeat_band(band,config['strip_y']-cut,config['strip_height'],growth)
    else:
        expanded = cv2.resize(band,(w,len(band)+growth),interpolation=cv2.INTER_LINEAR)
    y0 = cut+padding-growth
    opacity = expanded[...,3:4]
    base[y0:end+padding] = np.uint8(np.clip(expanded[...,:3]+base[y0:end+padding]*(1-opacity),0,255))
    # A small overlap hides the cut boundary; head pixels themselves are unscaled.
    overlap = 5
    head_end = cut+overlap
    head_alpha = mask[:head_end].copy()
    head_alpha[cut:] *= np.linspace(1,0,overlap)[:,None]
    y0 = padding-growth
    source_start = max(0,-y0)
    target_start = max(0,y0)
    count = head_end-source_start
    opacity = head_alpha[source_start:, :, None]
    base[target_start:target_start+count] = np.uint8(np.clip(
        rgb[source_start:head_end]*opacity+base[target_start:target_start+count]*(1-opacity),0,255))
    return Image.fromarray(base),padding


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config',type=Path,default=Path('examples/giraffe/manual-regions.json'))
    parser.add_argument('--output',type=Path,default=Path('examples/giraffe'))
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    original = load_image(Path(config['image'])).convert('RGB')
    rgb = np.array(original)
    mask = np.zeros(rgb.shape[:2],np.uint8)
    cv2.fillPoly(mask,[np.int32(config['polygon'])],255)
    # Only a narrow uncertain edge is refined; manual interior remains foreground.
    eroded = cv2.erode(mask,np.ones((9,9),np.uint8))
    dilated = cv2.dilate(mask,np.ones((9,9),np.uint8))
    labels = np.where(mask>0,cv2.GC_PR_FGD,cv2.GC_PR_BGD).astype(np.uint8)
    labels[eroded>0] = cv2.GC_FGD
    labels[dilated==0] = cv2.GC_BGD
    cv2.grabCut(rgb,labels,None,np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),3,cv2.GC_INIT_WITH_MASK)
    mask = np.uint8((labels==cv2.GC_FGD)|(labels==cv2.GC_PR_FGD))*255
    mask = cv2.GaussianBlur(mask,(0,0),.75).astype(np.float32)/255
    coefficients = background_fit(rgb,mask,config['cut_y'])
    Image.fromarray(np.uint8(mask*255)).save(args.output/'giraffe-manual-mask.png')
    guide = original.copy()
    draw = ImageDraw.Draw(guide)
    for y,color,label in ((config['cut_y'],'red','Head / neck cut'),(config['band_end'],'blue','Fixed lower boundary'),
                          (config['strip_y'],'yellow','Repeated strip')):
        draw.line((0,y,original.width,y),fill=color,width=3)
        draw.text((8,y+5),label,fill=color)
    guide.save(args.output/'giraffe-manual-regions.jpg',quality=95)
    for method in ('repeat','scale'):
        results = []
        for multiplier in (1,2):
            result,padding = render(rgb,mask,config,config['growth']*multiplier,method,coefficients)
            result.save(args.output/f'giraffe-manual-{method}-{multiplier}.png')
            results.append(result)
            # The body below the edited band must remain byte-for-byte unchanged.
            np.testing.assert_array_equal(np.array(result)[config['band_end']+padding:],rgb[config['band_end']:])
        sheet = Image.new('RGB',(1350,760),(25,25,25))
        draw = ImageDraw.Draw(sheet)
        for col,(label,picture) in enumerate((('Original',original),('+110px',results[0]),('+220px',results[1]))):
            draw.text((col*450+12,10),label+' | '+method,fill='white')
            picture = picture.copy()
            picture.thumbnail((430,710),Image.Resampling.LANCZOS)
            sheet.paste(picture,(col*450+(450-picture.width)//2,35+(710-picture.height)//2))
        sheet.save(args.output/f'giraffe-manual-{method}-comparison.jpg',quality=95)
        print(method,'body pixel check passed',flush=True)


if __name__=='__main__':
    main()
