"""CPU thermal imaging, night vision, and directional particle disintegration."""
import cv2
import numpy as np
from PIL import Image, ImageDraw

MODES = ('thermal', 'nightvision', 'thanos')


def apply_effect(image, mode):
    if mode not in MODES:
        raise ValueError('Unknown cinematic effect.')
    original = image.convert('RGBA')
    work = original.copy()
    work.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    pixels = np.asarray(work)
    rgb = pixels[..., :3].astype(np.float32)*(pixels[..., 3:4]/255)
    gray = rgb @ np.array([.2126, .7152, .0722], np.float32)
    h, w = gray.shape
    rng = np.random.default_rng(73)
    if mode == 'thermal':
        # Simulated heat from luminance; this does not measure temperature.
        heat = cv2.GaussianBlur(gray, (0, 0), .8)
        low, high = np.percentile(heat, (2, 98))
        heat = np.clip((heat-low)/max(1., high-low)*255, 0, 255).astype(np.uint8)
        colored = cv2.applyColorMap(heat, cv2.COLORMAP_INFERNO)[..., ::-1].copy()
        result = Image.fromarray(colored)
    elif mode == 'nightvision':
        light = cv2.createCLAHE(clipLimit=3., tileGridSize=(8, 8)).apply(gray.astype(np.uint8))/255
        light = np.sqrt(light)
        yy, xx = np.mgrid[:h, :w]
        vignette = np.clip(1.1-.65*((xx/max(1,w)-.5)**2+(yy/max(1,h)-.5)**2)*2, .15, 1)
        light = np.clip((light+rng.normal(0, .045, (h,w)))*vignette*(.78+.22*(yy%3 != 0)), 0, 1)
        result = Image.fromarray(np.uint8(np.stack((light*42, light*255, light*70), -1)))
    else:
        # Tear the right side into image-colored debris over a dim smoky field.
        background = Image.fromarray(np.uint8(np.clip(rgb*.17+np.array([12, 7, 18]), 0, 255)))
        yy, xx = np.mgrid[:h, :w]
        rough = cv2.resize(rng.random((max(2,h//22), max(2,w//22))).astype(np.float32), (w,h))
        boundary = w*(.51+.09*np.sin(yy/max(1,h)*8))
        keep = np.clip((boundary-xx)/(max(1,w)*.13)+rough*.8+.25, 0, 1)
        foreground = Image.fromarray(np.uint8(rgb))
        result = Image.composite(foreground, background, Image.fromarray(np.uint8(keep*255)))
        draw = ImageDraw.Draw(result)
        step = max(2, round(min(w,h)/160))
        for y in range(0,h,step):
            for x in range(max(0,round(w*.36)),w,step):
                if keep[y,x] > .95 or rng.random() > .38 or pixels[y,x,3] == 0:
                    continue
                progress = max(0., (x/w-.36)/.64)
                dx = round(x+rng.uniform(.02,.24)*w*progress)
                dy = round(y-rng.uniform(0,.12)*h*progress)
                size = max(1,round(step*rng.uniform(.4,1.4)))
                color = tuple(np.uint8(np.clip(rgb[y,x]*(1-progress*.5),0,255)))
                draw.rectangle((dx,dy,dx+size,dy+size), fill=color)
    if result.size != original.size:
        result = result.resize(original.size, Image.Resampling.LANCZOS)
    result = result.convert('RGBA')
    result.putalpha(original.getchannel('A'))
    return result
