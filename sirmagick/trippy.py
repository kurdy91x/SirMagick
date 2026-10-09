"""CPU-only zoom, mirror, swirl, and color-channel transformations."""

import cv2
import numpy as np
from PIL import Image


MODES = ("zoom", "tunnel", "kaleidoscope", "swirl", "rgbghost")


def apply_effect(image, mode):
    rgba = np.array(image.convert("RGBA"), dtype=np.float32)
    # Interpolate premultiplied colors to preserve transparent edges.
    rgba[..., :3] *= rgba[..., 3:4]/255
    height, width = rgba.shape[:2]
    xx, yy = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    cx, cy = (width-1)/2, (height-1)/2
    dx, dy = xx-cx, yy-cy
    radius = np.hypot(dx, dy)
    angle = np.arctan2(dy, dx)

    def sample(x, y):
        return cv2.remap(rgba, np.asarray(x, np.float32), np.asarray(y, np.float32),
                         cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT_101)

    if mode == "zoom":
        # Keep a crisp base and add progressively enlarged ghost exposures.
        output = rgba*.35
        weights = np.exp(-np.linspace(0, 2.0, 15))
        weights *= .65/weights.sum()
        for scale, weight in zip(np.linspace(1.04, 1.9, len(weights)), weights):
            output += sample(cx+dx/scale, cy+dy/scale)*weight
    elif mode == "tunnel":
        output = rgba.copy()
        # Repeated inset pictures form a rotated tunnel into the image.
        for level in range(1, 7):
            size = .73**level
            theta = level*.09
            u = (dx*np.cos(theta)+dy*np.sin(theta))/size
            v = (-dx*np.sin(theta)+dy*np.cos(theta))/size
            inside = np.maximum(np.abs(u)/(width*.49), np.abs(v)/(height*.49))
            blend = np.clip((1-inside)/.035, 0, 1)[..., None]
            output = output*(1-blend)+sample(cx+u, cy+v)*blend
    elif mode == "kaleidoscope":
        sector = np.pi/3
        folded = np.abs((angle+.17+sector/2) % sector-sector/2)
        # Offset the sampled wedge so recognizable features form the pattern.
        output = sample(cx+radius*np.sin(folded)-width*.13,
                        cy-radius*np.cos(folded)+height*.12)
    elif mode == "swirl":
        falloff = np.clip(1-radius/(min(width, height)*.78), 0, 1)
        theta = angle+3.8*falloff**2
        output = sample(cx+radius*np.cos(theta), cy+radius*np.sin(theta))
    elif mode == "rgbghost":
        offset = max(3, width*.035)
        red = sample(xx-offset, yy-height*.01)
        blue = sample(xx+offset, yy+height*.01)
        output = rgba.copy()
        output[..., 0] = red[..., 0]
        output[..., 2] = blue[..., 2]
        # Use the original alpha and discard shifted colors outside it.
        for channel, shifted in ((0, red), (2, blue)):
            straight = np.divide(shifted[..., channel]*255, shifted[..., 3],
                                 out=np.zeros((height, width), np.float32), where=shifted[..., 3]>0)
            output[..., channel] = straight*rgba[..., 3]/255
    else:
        raise ValueError(mode)
    np.divide(output[..., :3]*255, output[..., 3:4], out=output[..., :3], where=output[..., 3:4]>0)
    return Image.fromarray(np.clip(np.rint(output), 0, 255).astype(np.uint8))


