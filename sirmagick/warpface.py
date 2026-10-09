"""Warpface: Kopf-Collage mit lokal verkleinerten Originalmerkmalen."""

import math

import cv2
import numpy as np
from PIL import Image

from .chudthor import OVAL
from .data import Detection

EYES = ((33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246),
        (263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466))
MOUTH = (61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291,
         375, 321, 405, 314, 17, 84, 181, 91, 146)
NOSE = (5, 4, 1, 2, 98, 327, 97, 326, 94, 19)
HEAD_SCALE = 1.30
FEATURE_SCALE = 0.50


def _polygon_mask(size, points):
    mask = np.zeros((size[1], size[0]), dtype=np.uint8)
    cv2.fillConvexPoly(mask, cv2.convexHull(np.rint(points).astype(np.int32)), 255)
    return mask


def _shrink_features(rgba, points):
    """Merkmale lokal skalieren, umgebende Pixel schlie?en den ?bergangsring."""
    from .chudthor import radial_source, bilinear_rgba

    result = rgba.copy()
    height, width = rgba.shape[:2]
    for indices in (*EYES, NOSE, MOUTH):
        feature = points[list(indices)]
        center = (feature.min(axis=0)+feature.max(axis=0))/2
        extent = (feature.max(axis=0)-feature.min(axis=0))/2
        # Die Nase einschlie?lich Nasenfl?gel/Schatten markieren, Augen samt
        # Lidrand. Ein sehr flaches Auge erh?lt einen ausreichend hohen ?bergang.
        rx = max(2.0, extent[0]*(1.45 if indices == NOSE else 1.10))
        ry = max(2.0, extent[1]*1.25, rx*0.30)
        outer = 1.9
        x0, y0 = max(0, math.floor(center[0]-rx*outer)), max(0, math.floor(center[1]-ry*outer))
        x1, y1 = min(width, math.ceil(center[0]+rx*outer)+1), min(height, math.ceil(center[1]+ry*outer)+1)
        if x0 >= x1 or y0 >= y1:
            continue
        xx, yy = np.meshgrid(np.arange(x0, x1, dtype=np.float32),
                             np.arange(y0, y1, dtype=np.float32))
        dx, dy = (xx-center[0])/rx, (yy-center[1])/ry
        radius = np.hypot(dx, dy)
        source_radius = radial_source(radius, FEATURE_SCALE, outer)
        factor = np.divide(source_radius, radius, out=np.full_like(radius, 1/FEATURE_SCALE),
                           where=radius > 1e-6)
        source_x, source_y = center[0]+dx*factor*rx, center[1]+dy*factor*ry
        # Jeder Zielpixel erh?lt einen vorhandenen Quellpixel. Au?erhalb des
        # ?bergangsrings bleibt das Bild bitgenau erhalten, auch bei Alpha.
        sampled = bilinear_rgba(result, source_x, source_y)
        active = radius < outer
        target = result[y0:y1, x0:x1]
        target[active] = sampled[active]
    return result


def _head_mask(rgba, points, rx, ry):
    """Gesicht als sichere Saat; Haare/Kopfrand mit GrabCut annähern."""
    height, width = rgba.shape[:2]
    outline = points[list(OVAL)]
    center = (outline.min(axis=0)+outline.max(axis=0))/2
    head = outline-center
    head[:, 0] *= 1.16
    upper = head[:, 1] < 0
    head[upper, 1] *= 1.65
    head[~upper, 1] *= 1.04
    head += center
    probable = _polygon_mask((width, height), head)
    sure = _polygon_mask((width, height), outline)
    # Segmentierung auf begrenzter Auflösung, Originaltextur bleibt unberührt.
    factor = min(1.0, 512/max(width, height))
    small_size = (max(2, round(width*factor)), max(2, round(height*factor)))
    rgb = cv2.resize(rgba[..., :3], small_size, interpolation=cv2.INTER_AREA)
    probable_small = cv2.resize(probable, small_size, interpolation=cv2.INTER_NEAREST)
    sure_small = cv2.resize(sure, small_size, interpolation=cv2.INTER_NEAREST)
    labels = np.where(probable_small > 0, cv2.GC_PR_FGD, cv2.GC_BGD).astype(np.uint8)
    labels[sure_small > 0] = cv2.GC_FGD
    if np.any(labels == cv2.GC_BGD) and np.any(labels == cv2.GC_FGD):
        cv2.setRNGSeed(0)
        cv2.grabCut(rgb, labels, None, np.zeros((1, 65)), np.zeros((1, 65)),
                    3, cv2.GC_INIT_WITH_MASK)
        mask = np.where((labels == cv2.GC_FGD) | (labels == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)
        mask = cv2.resize(mask, (width, height), interpolation=cv2.INTER_LINEAR)
    else:
        mask = probable
    mask = np.maximum(mask, sure)
    mask = cv2.GaussianBlur(mask, (0, 0), max(0.8, rx*0.008))
    return mask


def _square_outer_cheeks(rgba, mask, points, rx, ry):
    """Nur schmale äußere Wangenstreifen verschieben; Mitte bleibt unverändert."""
    height, width = rgba.shape[:2]
    outline = points[list(OVAL)]
    center = (outline.min(axis=0)+outline.max(axis=0))/2
    xx, yy = np.meshgrid(np.arange(width, dtype=np.float32), np.arange(height, dtype=np.float32))
    dx, dy = (xx-center[0])/rx, (yy-center[1])/ry
    side = np.clip((np.abs(dx)-0.55)/0.35, 0, 1)
    # Lokale, geringe Konturänderung, kein radialer Ganzgesichtsfilter.
    vertical = np.exp(-((dy-0.55)/0.48)**4)
    outside = np.clip((1.5-np.abs(dx))/0.35, 0, 1)
    source_x = (xx-np.sign(dx)*rx*0.09*side*vertical*outside).astype(np.float32)
    shaped = cv2.remap(rgba, source_x, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    shaped_mask = cv2.remap(mask, source_x, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return shaped, shaped_mask


def apply_warpface(image: Image.Image, detection: Detection) -> Image.Image:
    detection.require("face")
    if image.size != (detection.width, detection.height):
        raise ValueError("Erkennungsdaten passen nicht zur Bildgröße.")
    result = image.convert("RGBA").copy()
    # Große Köpfe zuerst, kleinere Köpfe bei Überlappung darüber einsetzen.
    faces = sorted(detection.faces, key=lambda f: -abs(f[454].x-f[234].x))
    original = np.array(image.convert("RGBA"))
    width, height = image.size
    for face in faces:
        points = np.array([(p.x, p.y) for p in face], dtype=np.float32)
        outline = points[list(OVAL)]
        center = (outline.min(axis=0)+outline.max(axis=0))/2
        rx, ry = np.maximum(2, (outline.max(axis=0)-outline.min(axis=0))/2)
        x0 = max(0, math.floor(center[0]-rx*1.6))
        x1 = min(width, math.ceil(center[0]+rx*1.6))
        y0 = max(0, math.floor(center[1]-ry*2.0))
        y1 = min(height, math.ceil(center[1]+ry*1.2))
        if x1-x0 < 3 or y1-y0 < 3:
            continue
        local = points-[x0, y0]
        crop = original[y0:y1, x0:x1].copy()
        mask = _head_mask(crop, local, rx, ry)
        edited = _shrink_features(crop, local)
        edited, mask = _square_outer_cheeks(edited, mask, local, rx, ry)
        edited[..., 3] = np.rint(edited[..., 3].astype(np.float32)*mask/255).astype(np.uint8)
        head = Image.fromarray(edited)
        size = (max(1, round(head.width*HEAD_SCALE)), max(1, round(head.height*HEAD_SCALE)))
        head = head.resize(size, Image.Resampling.LANCZOS)
        # Am Hals verankern, Kopf wächst überwiegend nach oben und zur Seite.
        anchor = np.array([center[0], center[1]+ry*1.05])
        left = round(anchor[0]+(x0-anchor[0])*HEAD_SCALE)
        top = round(anchor[1]+(y0-anchor[1])*HEAD_SCALE)
        result.alpha_composite(head, (left, top))
    return result
