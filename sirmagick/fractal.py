"""Bounded CPU fractals colored with the input image."""

import cv2
import numpy as np
from PIL import Image

MODES = ("julia", "newton")


def _field(width, height, mode):
    # Bound iteration cost independently of the input's pixel count.
    scale = min(1., 800/max(width, height))
    w, h = max(1, round(width*scale)), max(1, round(height*scale))
    xx, yy = np.meshgrid(np.linspace(-1.65, 1.65, w, dtype=np.float32),
                         np.linspace(-1.65, 1.65, h, dtype=np.float32))
    z = (xx+1j*yy).astype(np.complex64)
    if mode == "julia":
        active = np.ones(z.shape, bool)
        count = np.full(z.shape, 96., np.float32)
        for step in range(96):
            z[active] = z[active]*z[active]+complex(-.745, .186)
            escaped = active & (np.abs(z) > 4)
            if escaped.any():
                count[escaped] = step+1-np.log2(np.maximum(1., np.log2(np.abs(z[escaped]))))
            active &= ~escaped
            if not active.any():
                break
        phase = np.angle(z)
        u = .5+.43*np.cos(phase+count*.19)
        v = .5+.43*np.sin(phase-count*.13)
        weight = .5+.5*np.cos(count*.62)
    else:
        count = np.zeros(z.shape, np.float32)
        active = np.ones(z.shape, bool)
        for step in range(40):
            derivative = 3*z*z
            safe = active & (np.abs(derivative) > 1e-7)
            z[safe] -= (z[safe]**3-1)/derivative[safe]
            # The pole at zero stays bounded and gets a defined basin.
            z[active & ~safe] = 1
            z = np.clip(z.real, -100, 100)+1j*np.clip(z.imag, -100, 100)
            count[active] += 1
            active &= np.abs(z**3-1) > 1e-4
            if not active.any():
                break
        phase = np.angle(z)
        u = .5+.40*np.cos(phase+xx*.65+count*.12)
        v = .5+.40*np.sin(phase+yy*.65-count*.12)
        weight = .5+.5*np.cos(count*.85)
    return tuple(cv2.resize(a.astype(np.float32), (width, height), interpolation=cv2.INTER_LINEAR)
                 for a in (u, v, weight))


def apply_effect(image, mode):
    if mode not in MODES:
        raise ValueError("Unknown fractal effect.")
    source = np.asarray(image.convert("RGBA"), np.float32)
    width, height = image.size
    u, v, contours = _field(width, height, mode)
    rgba = source.copy()
    rgba[..., :3] *= rgba[..., 3:4]/255
    sampled = cv2.remap(rgba, u*(width-1), v*(height-1), cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REFLECT_101)
    np.divide(sampled[..., :3]*255, sampled[..., 3:4],
              out=sampled[..., :3], where=sampled[..., 3:4]>0)
    # Input texture and colors remain visible through fractal bands.
    amount = (.55+.23*contours)[..., None]
    rgb = source[..., :3]*(1-amount)+sampled[..., :3]*amount
    rgb *= (.72+.28*contours)[..., None]
    output = np.dstack((np.clip(np.rint(rgb), 0, 255).astype(np.uint8), source[..., 3].astype(np.uint8)))
    return Image.fromarray(output)
