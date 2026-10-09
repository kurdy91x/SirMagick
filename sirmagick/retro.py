"""Fixed-strength retro treatments and fisheye."""
import cv2
import numpy as np
from PIL import Image

from .chudthor import bilinear_rgba

MODES = ("glitch", "crt", "halftone", "fisheye")


def apply_effect(image, mode, detection=None):
    if mode not in MODES:
        raise ValueError("Unknown retro effect.")
    pixels = np.array(image.convert("RGBA"))
    height, width = pixels.shape[:2]
    if mode == "fisheye":
        xx, yy = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
        cx, cy = (width-1)/2, (height-1)/2
        scale = max(1., min(width, height)*.5)
        dx, dy = (xx-cx)/scale, (yy-cy)/scale
        radius = np.hypot(dx, dy)
        # Identity at the lens boundary, magnification in the center.
        factor = np.where(radius < 1, .40+.60*radius**2, 1)
        return Image.fromarray(bilinear_rgba(pixels, cx+dx*factor*scale, cy+dy*factor*scale))
    rgb = pixels[..., :3].astype(np.float32)
    if mode == "glitch":
        rng = np.random.default_rng(713)
        result = rgb.copy()
        shift = max(1, round(width*.012))
        result[..., 0] = np.roll(rgb[..., 0], shift, axis=1)
        result[..., 2] = np.roll(rgb[..., 2], -shift, axis=1)
        for _ in range(12):
            start = int(rng.integers(height))
            end = min(height, start+max(1, int(height*rng.uniform(.008, .04))))
            offset = int(rng.choice([-1, 1])*width*rng.uniform(.03, .13))
            result[start:end] = np.roll(result[start:end], offset, axis=1)
            if rng.random() < .35:
                result[start:end] = result[start:end]*.65+np.array([65, 5, 45])
        rgb = result
    elif mode == "crt":
        yy, xx = np.mgrid[:height, :width].astype(np.float32)
        u = (xx-(width-1)/2)/max(1., width/2)
        v = (yy-(height-1)/2)/max(1., height/2)
        factor = 1+.18*(u*u+v*v)
        sampled = bilinear_rgba(pixels, (width-1)/2+u*factor*width/2,
                                (height-1)/2+v*factor*height/2)
        rgb = sampled[..., :3].astype(np.float32)
        rgb[..., 0] = np.roll(rgb[..., 0], max(1, round(width*.006)), axis=1)
        rgb[..., 2] = np.roll(rgb[..., 2], -max(1, round(width*.006)), axis=1)
        period = max(3, round(height/150))
        scan = np.where((yy.astype(int) % period) < max(1, round(period*.38)), .40, 1.)
        vignette = np.clip(1-.32*(u*u+v*v), .25, 1)
        rgb = 255*np.power(rgb/255, .88)
        glow = cv2.GaussianBlur(rgb, (0, 0), max(.6, width/350))
        rgb = (rgb*.95+glow*.22)*(scan*vignette)[..., None]
        phosphor = (xx.astype(int)//max(1, width//480)) % 3
        for channel in range(3):
            rgb[..., channel] *= np.where(phosphor == channel, 1., .80)
        screen = (np.abs(u*factor) <= 1) & (np.abs(v*factor) <= 1)
        rgb *= screen[..., None]
        pixels[..., 3] = sampled[..., 3]
    elif mode == "halftone":
        cell = max(4, round(min(width, height)/95))
        yy, xx = np.mgrid[:height, :width]
        small = cv2.resize(rgb, (max(1, (width+cell-1)//cell), max(1, (height+cell-1)//cell)), interpolation=cv2.INTER_AREA)
        colors = small[np.minimum(yy//cell, small.shape[0]-1), np.minimum(xx//cell, small.shape[1]-1)]
        light = colors @ np.array([.2126, .7152, .0722])/255
        radius = np.sqrt(1-light)*cell*.72
        distance = np.hypot(xx % cell-(cell-1)/2, yy % cell-(cell-1)/2)
        ink = np.clip(radius-distance+.5, 0, 1)[..., None]
        paper = colors*.35+np.array([255, 249, 231])*.65
        rgb = paper*(1-ink)+(np.floor(colors/48)*48*.50)*ink
    pixels[..., :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    return Image.fromarray(pixels)
