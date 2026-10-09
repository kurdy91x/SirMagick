"""Complex-coordinate image transformations with bounded singularities."""

import cv2
import numpy as np
from PIL import Image


MODES = ("droste", "complexsquare", "complexexp", "logpolar", "inversion")


def coordinate_map(width, height, mode):
    xx, yy = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    cx, cy = (width-1)/2, (height-1)/2
    unit = min(width, height)/2
    z = (xx-cx)/unit + 1j*(yy-cy)/unit
    radius = np.maximum(np.abs(z), .015)
    theta = np.angle(z)
    if mode == "complexsquare":
        source = z*z*.85
    elif mode == "complexexp":
        # Exponential repeats vertically, with increasing scale horizontally.
        source = .43*np.exp(1.7*z)-.35
    elif mode == "inversion":
        # Regularize the pole at zero; elsewhere this is exactly 0.55 / z.
        source = .55*np.conj(z)/np.maximum(np.abs(z)**2, .025**2)
    elif mode == "logpolar":
        # Inverse of a log-polar transform: horizontal axis = angle,
        # vertical axis = log radius. Circles become straight image rows.
        angle = (xx/max(1, width-1)*2-1)*np.pi
        log_radius = np.log(.035)+(yy/max(1, height-1))*np.log(1.65/.035)
        source = np.exp(log_radius+1j*angle)
    elif mode == "droste":
        # Twist log coordinates and periodically repeat the radial interval.
        # This creates nested spiral copies, not a swirl of one exposure.
        logarithm = np.log(radius)
        period = np.log(3.0)
        wrapped = np.mod(logarithm+.34*theta, period)
        mapped_radius = .28*np.exp(wrapped)
        mapped_angle = theta-.95*logarithm+.3
        source = mapped_radius*np.exp(1j*mapped_angle)
    else:
        raise ValueError(mode)
    source_x = np.asarray(cx+source.real*unit, np.float32)
    source_y = np.asarray(cy+source.imag*unit, np.float32)
    if not (np.isfinite(source_x).all() and np.isfinite(source_y).all()):
        raise ValueError("Non-finite coordinate mapping")
    return source_x, source_y


def apply_effect(image, mode):
    rgba = np.asarray(image.convert("RGBA"), np.float32).copy()
    rgba[..., :3] *= rgba[..., 3:4]/255
    source_x, source_y = coordinate_map(image.width, image.height, mode)
    output = cv2.remap(rgba, source_x, source_y, cv2.INTER_LINEAR,
                       borderMode=cv2.BORDER_REFLECT_101)
    np.divide(output[..., :3]*255, output[..., 3:4],
              out=output[..., :3], where=output[..., 3:4]>0)
    return Image.fromarray(np.clip(np.rint(output), 0, 255).astype(np.uint8))


