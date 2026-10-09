"""Local facial feature transforms and full-image ultrawide scaling."""
import math
import secrets

import numpy as np
import cv2
from PIL import Image
from .chudthor import OVAL, bilinear_rgba, radial_source
from .warpface import EYES, MOUTH, NOSE

MODES = ("fatmagic", "tinyface", "bigmouth", "googly", "wide", "eyeswap")


def replace_features_with_eyes(image, detection):
    """Remove nose/mouth texture, then blend copies of an original eye in place."""
    detection.require("face")
    original = np.array(image.convert("RGBA"))
    result = original[..., :3].copy()
    height, width = result.shape[:2]
    for face in detection.faces:
        points = np.array([(p.x, p.y) for p in face], np.float32)
        # Use the wider visible eye; all source patches come from the original.
        eye = max((points[list(indices)] for indices in EYES), key=lambda p: np.ptp(p[:, 0]))
        low = np.maximum(0, np.floor(eye.min(axis=0)-[3, 4])).astype(int)
        high = np.minimum([width, height], np.ceil(eye.max(axis=0)+[4, 5])).astype(int)
        patch = original[low[1]:high[1], low[0]:high[0], :3].copy()
        if min(patch.shape[:2]) < 3:
            continue
        for indices, enlargement in ((NOSE, 1.55), (MOUTH, 1.15)):
            feature = points[list(indices)]
            center = np.rint((feature.min(axis=0)+feature.max(axis=0))/2).astype(int)
            extent = np.maximum(3, (feature.max(axis=0)-feature.min(axis=0))/2)
            removal = np.zeros((height, width), np.uint8)
            axes = tuple(np.ceil(extent*[1.5, 1.6]+2).astype(int))
            cv2.ellipse(removal, tuple(center), axes, 0, 0, 360, 255, -1)
            result = cv2.inpaint(result, removal, 5, cv2.INPAINT_TELEA)
            target_width = max(8, round(extent[0]*2*enlargement))
            target_height = max(6, round(target_width*patch.shape[0]/patch.shape[1]))
            target_width = min(target_width, width-4)
            target_height = min(target_height, height-4)
            if target_width < 6 or target_height < 6:
                continue
            resized = cv2.resize(patch, (target_width, target_height), interpolation=cv2.INTER_CUBIC)
            mask = np.zeros((target_height, target_width), np.uint8)
            cv2.ellipse(mask, (target_width//2, target_height//2),
                        (max(1, target_width//2-2), max(1, target_height//2-2)), 0, 0, 360, 255, -1)
            center[0] = np.clip(center[0], target_width//2+1, width-(target_width+1)//2-1)
            center[1] = np.clip(center[1], target_height//2+1, height-(target_height+1)//2-1)
            result = cv2.seamlessClone(resized, result, mask, tuple(center), cv2.NORMAL_CLONE)
    return Image.fromarray(np.dstack((result, original[..., 3])))


def local_scale(pixels, points, scale, outer=2.6, padding=(1.2, 1.4), horizontal=False):
    points = np.asarray(points, dtype=np.float32)
    center = (points.min(axis=0) + points.max(axis=0))/2
    radii = np.maximum(3, (points.max(axis=0)-points.min(axis=0))/2 * padding)
    radii[1] = max(radii[1], radii[0]*0.3)
    height, width = pixels.shape[:2]
    low = np.maximum([0, 0], np.floor(center-radii*outer)).astype(int)
    high = np.minimum([width, height], np.ceil(center+radii*outer+1)).astype(int)
    x0, y0 = low
    x1, y1 = high
    if x0 >= x1 or y0 >= y1:
        return
    xx, yy = np.meshgrid(np.arange(x0, x1, dtype=np.float32), np.arange(y0, y1, dtype=np.float32))
    dx, dy = xx-center[0], yy-center[1]
    radius = np.hypot(dx/radii[0], dy/radii[1])
    mapped = radial_source(radius, scale, outer)
    factor = np.divide(mapped, radius, out=np.full_like(radius, 1/scale), where=radius>1e-6)
    sx = center[0]+dx*factor
    sy = yy if horizontal else center[1]+dy*factor
    sampled = bilinear_rgba(pixels, sx, sy)
    target = pixels[y0:y1, x0:x1]
    target[radius < outer] = sampled[radius < outer]


def apply_mode(image, detection, mode):
    if mode == "random":
        return apply_mode(image, detection, secrets.choice(MODES))
    if mode == "eyeswap":
        return replace_features_with_eyes(image, detection)
    if mode == "wide":
        return image.resize((image.width*3, image.height), Image.Resampling.LANCZOS)
    detection.require("face")
    result = np.array(image.convert("RGBA"))
    if mode == "fatmagic":
        for pose in detection.poses:
            torso = [pose[i] for i in (11, 12, 23, 24) if pose[i].visibility > .5]
            if len(torso) == 4:
                local_scale(result, [(p.x, p.y) for p in torso], 1.55, outer=2.5,
                            padding=(1.25, 1.45), horizontal=True)
    for face in detection.faces:
        points = np.array([(p.x, p.y) for p in face], dtype=np.float32)
        if mode == "tinyface":
            indices = tuple(set((*EYES[0], *EYES[1], *NOSE, *MOUTH)))
            local_scale(result, points[list(indices)], .48, outer=1.65, padding=(1.1, 1.1))
        elif mode == "bigmouth":
            local_scale(result, points[list(MOUTH)], 1.85, outer=3.1, padding=(1.2, 1.3))
        elif mode == "googly":
            for eye in EYES:
                local_scale(result, points[list(eye)], 1.8, outer=2.8, padding=(1.25, 1.5))
        elif mode == "fatmagic":
            # Prototype: widen the face too, without relying on a body mask.
            local_scale(result, points[list(OVAL)], 1.32, outer=1.8,
                        padding=(1.0, 1.05), horizontal=True)
        else:
            raise ValueError(mode)
    return Image.fromarray(result)


