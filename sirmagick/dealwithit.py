"""Position the supplied pixel shades and blunt using face landmarks."""
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np
from PIL import Image


@lru_cache(maxsize=2)
def _asset(name):
    with Image.open(Path(__file__).parent / 'assets' / name) as image:
        return np.asarray(image.convert('RGBA')).copy()


def _place(canvas, asset, anchor, position, width, axis):
    scale = width/asset.shape[1]
    a, b = axis*scale
    matrix = np.array([[a, -b, position[0]-a*anchor[0]+b*anchor[1]],
                       [b, a, position[1]-b*anchor[0]-a*anchor[1]]], np.float32)
    # Premultiply before interpolation to avoid dark outlines around transparent edges.
    premult = asset.astype(np.float32)/255
    premult[..., :3] *= premult[..., 3:4]
    warped = cv2.warpAffine(premult, matrix, canvas.size, flags=cv2.INTER_LINEAR)
    alpha = warped[..., 3:4]
    warped[..., :3] /= np.maximum(alpha, 1e-6)
    canvas.alpha_composite(Image.fromarray(np.uint8(np.clip(warped*255,0,255))))


def _mouth_attachment(points, axis, center, span, blunt):
    # Nose displacement along the eye axis estimates which way the face turns.
    facing_left = float((points[1]-center) @ axis) < -.03*span
    if facing_left:
        return blunt, (blunt.shape[1]*.97, blunt.shape[0]*.07), points[61]
    mirrored = np.ascontiguousarray(blunt[:, ::-1])
    return mirrored, (blunt.shape[1]*.03, blunt.shape[0]*.07), points[291]


def apply_dealwithit(image, detection):
    detection.require('face')
    result = image.convert('RGBA').copy()
    shades, blunt = _asset('shades.png'), _asset('blunt.png')
    for face in detection.faces:
        points = np.array([(p.x,p.y) for p in face])
        axis = points[263]-points[33]
        span = max(1.,float(np.linalg.norm(axis)))
        axis /= span
        center = (points[33]+points[263])/2
        _place(result, shades, (shades.shape[1]/2,shades.shape[0]*.25), center, span*1.48, axis)
        oriented, anchor, mouth = _mouth_attachment(points, axis, center, span, blunt)
        _place(result, oriented, anchor, mouth, span*.82, axis)
    result.putalpha(image.convert('RGBA').getchannel('A'))
    return result
