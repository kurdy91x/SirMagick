"""Texturerhaltende Gesichtsverformung mit festen, wiederholbaren Proportionen.

Inverse Abbildung verhindert Löcher: jedes Zielpixel liest einen Quellpunkt.
Nur lokale Bildausschnitte werden verarbeitet; außerhalb bleibt das Bild identisch.
"""

import math

import numpy as np
from PIL import Image

from .data import Detection

# MediaPipe-Gesichtskontur; Iris und herausragende Merkmale nicht für die Größe nutzen.
OVAL = (10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
        397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
        172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109)


def radial_source(radius, boundary, outer):
    """Zielkontur boundary auf Quellkontur 1 abbilden, außen glatt Identität.

    Kubische Hermite-Interpolation verbindet Skalierung und unverändertes Umfeld
    mit stetiger erster Ableitung. boundary darf ein Feld pro Richtung sein.
    """
    span = outer - boundary
    secant = (outer - 1) / span
    slope_start = 1 / boundary
    slope_end = np.ones_like(boundary)
    # Monotonie begrenzt die Tangenten: keine gefalteten Pixelringe bei
    # starker Verkleinerung der inneren Gesichtszüge.
    limiter = np.minimum(1, 3 / np.hypot(slope_start/secant, slope_end/secant))
    slope_start = slope_start * limiter
    slope_end = slope_end * limiter
    t = np.clip((radius - boundary) / span, 0, 1)
    mapped = ((2*t**3 - 3*t**2 + 1)
              + (t**3 - 2*t**2 + t) * span * slope_start
              + (-2*t**3 + 3*t**2) * outer
              + (t**3 - t**2) * span * slope_end)
    inner_t = np.clip(radius/boundary, 0, 1)
    inner = inner_t + (inner_t**3-inner_t**2)*boundary*(slope_start-1/boundary)
    return np.where(radius <= boundary, inner,
                    np.where(radius >= outer, radius, mapped))


def bilinear_rgba(pixels, x, y):
    """Alpha vor Interpolation gewichten, damit transparente Ränder nicht abdunkeln."""
    height, width = pixels.shape[:2]
    x = np.clip(x, 0, width - 1)
    y = np.clip(y, 0, height - 1)
    x0, y0 = np.floor(x).astype(int), np.floor(y).astype(int)
    x1, y1 = np.minimum(x0 + 1, width - 1), np.minimum(y0 + 1, height - 1)
    wx, wy = (x-x0)[..., None], (y-y0)[..., None]
    accum = np.zeros((*x.shape, 4), dtype=np.float32)
    for ix, iy, weight in ((x0, y0, (1-wx)*(1-wy)), (x1, y0, wx*(1-wy)),
                           (x0, y1, (1-wx)*wy), (x1, y1, wx*wy)):
        sample = pixels[iy, ix].astype(np.float32)
        sample[..., :3] *= sample[..., 3:4] / 255
        accum += sample * weight
    np.divide(accum[..., :3] * 255, accum[..., 3:4],
              out=accum[..., :3], where=accum[..., 3:4] > 0)
    return np.clip(np.rint(accum), 0, 255).astype(np.uint8)


def apply_chudthor(image: Image.Image, detection: Detection) -> Image.Image:
    detection.require("face")
    if image.size != (detection.width, detection.height):
        raise ValueError("Erkennungsdaten passen nicht zur Bildgröße.")
    pixels = np.array(image.convert("RGBA"))
    height, width = pixels.shape[:2]
    # Große Gesichter zuerst, stabile Reihenfolge bei gleich großen Gesichtern.
    faces = sorted(detection.faces,
                   key=lambda face: -abs(face[454].x-face[234].x))
    for face in faces:
        outline = np.array([(face[i].x, face[i].y) for i in OVAL])
        # Augenlinie liefert die Drehung des Kopfes im Bild.
        left, right = face[33], face[263]
        angle = math.atan2(right.y-left.y, right.x-left.x)
        cosine, sine = math.cos(angle), math.sin(angle)
        center = outline.mean(axis=0)
        relative = outline - center
        local_x = relative[:, 0]*cosine + relative[:, 1]*sine
        local_y = -relative[:, 0]*sine + relative[:, 1]*cosine
        cx_local = (local_x.min()+local_x.max())/2
        cy_local = (local_y.min()+local_y.max())/2
        center += (cx_local*cosine-cy_local*sine,
                   cx_local*sine+cy_local*cosine)
        rx = max(2.0, (local_x.max()-local_x.min())/2)
        ry = max(2.0, (local_y.max()-local_y.min())/2)
        features = []
        for indices in ((33, 133, 159, 145), (263, 362, 386, 374),
                        (61, 291, 0, 17, 13, 14), (98, 327, 1, 168, 2)):
            points = np.array([(face[i].x-center[0], face[i].y-center[1]) for i in indices])
            px = (points[:, 0]*cosine+points[:, 1]*sine)/rx
            py = (-points[:, 0]*sine+points[:, 1]*cosine)/ry
            feature_x, feature_y = (px.min()+px.max())/2, (py.min()+py.max())/2
            feature_rx = max(0.07, (px.max()-px.min())*0.72)
            feature_ry = max(0.06, (py.max()-py.min())*0.85, feature_rx*rx/ry*0.48)
            features.append((feature_x, feature_y, feature_rx, feature_ry))
        extent_x = 2.3*(abs(cosine)*rx + abs(sine)*ry)
        extent_y = 2.3*(abs(sine)*rx + abs(cosine)*ry)
        x0, x1 = max(0, math.floor(center[0]-extent_x)), min(width, math.ceil(center[0]+extent_x)+1)
        y0, y1 = max(0, math.floor(center[1]-extent_y)), min(height, math.ceil(center[1]+extent_y)+1)
        if x0 >= x1 or y0 >= y1:
            continue
        # Pro Gesicht aus einem unveränderten Quellausschnitt lesen; zeilenweise
        # Blöcke begrenzen den Speicher auch bei großen Eingabebildern.
        source = pixels[y0:y1, x0:x1].copy()
        for row in range(y0, y1, 128):
            end = min(row+128, y1)
            xx, yy = np.meshgrid(np.arange(x0, x1, dtype=np.float32),
                                 np.arange(row, end, dtype=np.float32))
            dx, dy = xx-center[0], yy-center[1]
            ux = (dx*cosine+dy*sine)/rx
            uy = (-dx*sine+dy*cosine)/ry
            radius = np.hypot(ux, uy)
            safe = np.maximum(radius, 1e-6)
            # Superellipse mit weichen Ecken: größer und leicht viereckig.
            direction = np.maximum(np.abs(ux/safe)**3 + np.abs(uy/safe)**3, 1e-6)**(-1/3)
            direction = np.where(radius > 1e-6, direction, 1.0)
            boundary = 1.38*direction
            mapped = radial_source(radius, boundary, 2.3)
            factor = np.where(radius > 1e-6, mapped/safe, 1/1.38)
            sx, sy = ux*factor, uy*factor
            # Merkmale einzeln verkleinern; die Haut dazwischen bleibt erhalten.
            for feature_x, feature_y, feature_rx, feature_ry in features:
                target_x, target_y = feature_x*0.90, 0.14+(feature_y-0.14)*0.90
                fx, fy = (sx-target_x)/feature_rx, (sy-target_y)/feature_ry
                fr = np.hypot(fx, fy)
                fs = np.maximum(fr, 1e-6)
                fm = radial_source(fr, 0.48, 1.8)
                ff = np.where(fr > 1e-6, fm/fs, 1/0.48)
                weight = np.clip((1.8-fr)/(1.8-0.48), 0, 1)
                weight = weight*weight*(3-2*weight)
                sx = target_x+fx*ff*feature_rx+(feature_x-target_x)*weight
                sy = target_y+fy*ff*feature_ry+(feature_y-target_y)*weight
            source_x = center[0]+sx*rx*cosine-sy*ry*sine
            source_y = center[1]+sx*rx*sine+sy*ry*cosine
            sampled = bilinear_rgba(source, source_x-x0, source_y-y0)
            active = radius < 2.3
            block = pixels[row:end, x0:x1]
            block[active] = sampled[active]
    return Image.fromarray(pixels)
