"""CPU-only pseudo-depth effects; no estimated scene geometry is required."""
import cv2
import numpy as np
from PIL import Image

MODES = ("extrude", "emboss")


def apply_effect(image, mode):
    if mode not in MODES:
        raise ValueError("Unknown depth effect.")
    pixels = np.array(image.convert("RGBA"))
    rgb = pixels[..., :3].astype(np.float32)
    height, width = pixels.shape[:2]
    # Hidden RGB cannot influence relief or contour detection.
    alpha = pixels[..., 3:4].astype(np.float32)/255
    visible = rgb*alpha+128*(1-alpha)
    gray = cv2.cvtColor(visible, cv2.COLOR_RGB2GRAY)/255
    if mode == "emboss":
        smooth = cv2.GaussianBlur(gray, (0, 0), max(.7, min(width, height)/650))
        dx = cv2.Sobel(smooth, cv2.CV_32F, 1, 0, ksize=3, scale=1/8)*18
        dy = cv2.Sobel(smooth, cv2.CV_32F, 0, 1, ksize=3, scale=1/8)*18
        norm = np.sqrt(dx*dx+dy*dy+1)
        diffuse = np.clip((-.48*dx-.60*dy+.64)/norm, 0, 1)
        shine = np.clip((-.32*dx-.40*dy+.86)/norm, 0, 1)**18
        metal = np.clip(35+diffuse*180+shine*90, 0, 255)
        rgb = metal[..., None]*np.array([.93, .98, 1.04])+visible*.07
    else:
        # Find broad contours at bounded resolution, not every skin pore.
        scale = min(1., 1024/max(width, height))
        w, h = max(1, round(width*scale)), max(1, round(height*scale))
        small = cv2.resize(gray, (w, h), interpolation=cv2.INTER_AREA)
        small = cv2.GaussianBlur(small, (0, 0), 1.)
        edges = cv2.Canny(np.clip(small*255, 0, 255).astype(np.uint8), 65, 145)/255
        edges = edges.astype(np.float32)
        trail = np.zeros_like(edges)
        distance = np.zeros_like(edges)
        length = max(3, round(min(w, h)*.035))
        for step in range(1, min(length, 32)+1):
            offset = step*length/min(length, 32)
            moved = cv2.warpAffine(edges, np.array([[1, 0, offset], [0, 1, offset*.65]], np.float32),
                                   (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            fresh = moved > trail
            distance[fresh] = offset/length
            trail = np.maximum(trail, moved)
        side = np.clip(trail-edges, 0, 1)
        shadow = cv2.GaussianBlur(trail, (0, 0), max(1., length*.15))
        side = cv2.resize(side, (width, height), interpolation=cv2.INTER_LINEAR)
        shadow = cv2.resize(shadow, (width, height), interpolation=cv2.INTER_LINEAR)
        distance = cv2.resize(distance, (width, height), interpolation=cv2.INTER_LINEAR)
        cyan, gold = np.array([35, 195, 215]), np.array([235, 130, 65])
        walls = cyan*(1-distance[..., None])+gold*distance[..., None]
        rgb *= 1-.50*shadow[..., None]
        amount = .88*side[..., None]
        rgb = rgb*(1-amount)+walls*amount
    output = pixels.copy()
    output[..., :3] = np.clip(np.rint(rgb), 0, 255).astype(np.uint8)
    return Image.fromarray(output)
