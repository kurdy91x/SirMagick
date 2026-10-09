"""Gesichtsfläche einheitlich verkleinern, nur den äußeren Hautstreifen ziehen."""

import math
import numpy as np
from PIL import Image

from .chudthor import OVAL, bilinear_rgba
from .data import Detection

FACE_SCALE = 0.84
INNER_RADIUS = 0.88


def _face_geometry(face):
    outline = np.array([(face[i].x, face[i].y) for i in OVAL], np.float32)
    eyes = np.array([face[263].x-face[33].x, face[263].y-face[33].y])
    angle = math.atan2(eyes[1], eyes[0])
    basis = np.array([[math.cos(angle), -math.sin(angle)],
                      [math.sin(angle), math.cos(angle)]], np.float32)
    center = outline.mean(axis=0)
    local = (outline-center) @ basis
    center += ((local.min(axis=0)+local.max(axis=0))/2) @ basis.T
    radii = np.maximum(2, np.max(np.abs((outline-center) @ basis), axis=0))
    normalized = ((outline-center) @ basis)/radii
    angles = np.arctan2(normalized[:, 1], normalized[:, 0])
    distances = np.linalg.norm(normalized, axis=1)
    order = np.argsort(angles)
    return outline, center, basis, radii, angles[order], distances[order]


def _source_radius(radius):
    """Innen exakt einheitlich skalieren, im Hautstreifen stetig anschließen."""
    target_inner = INNER_RADIUS*FACE_SCALE
    outer = INNER_RADIUS+(radius-target_inner)*(1-INNER_RADIUS)/(1-target_inner)
    return np.where(radius <= target_inner, radius/FACE_SCALE,
                    np.where(radius < 1, outer, radius))


def _face_map(face, width, height):
    outline, center, basis, radii, angles, distances = _face_geometry(face)
    low = np.maximum(0, np.floor(outline.min(axis=0)-1)).astype(int)
    high = np.minimum([width, height], np.ceil(outline.max(axis=0)+2)).astype(int)
    x0, y0 = low
    x1, y1 = high
    if x0 >= x1 or y0 >= y1:
        raise ValueError("Gesicht liegt außerhalb des Bildes.")
    xx, yy = np.meshgrid(np.arange(x0, x1, dtype=np.float32),
                         np.arange(y0, y1, dtype=np.float32))
    dx, dy = xx-center[0], yy-center[1]
    ux = (dx*basis[0, 0]+dy*basis[1, 0])/radii[0]
    uy = (dx*basis[0, 1]+dy*basis[1, 1])/radii[1]
    # Tatsächliche Landmark-Kontur statt einer Ellipse über Haaren/Hintergrund.
    contour_radius = np.interp(np.arctan2(uy, ux), angles, distances, period=2*np.pi)
    radius = np.hypot(ux, uy)/np.maximum(contour_radius, 1e-6)
    source_radius = _source_radius(radius)
    factor = np.divide(source_radius, radius, out=np.full_like(radius, 1/FACE_SCALE),
                       where=radius > 1e-6)
    source_x = center[0]+dx*factor
    source_y = center[1]+dy*factor
    return (x0, y0, x1, y1), source_x, source_y, radius < 1, radius


def apply_blockface(image: Image.Image, detection: Detection) -> Image.Image:
    detection.require("face")
    if image.size != (detection.width, detection.height):
        raise ValueError("Erkennungsdaten passen nicht zur Bildgröße.")
    original = np.array(image.convert("RGBA"))
    result = original.copy()
    width, height = image.size
    for face in detection.faces:
        bounds, source_x, source_y, active, _ = _face_map(face, width, height)
        x0, y0, x1, y1 = bounds
        source = original[y0:y1, x0:x1]
        target = result[y0:y1, x0:x1]
        for row in range(0, y1-y0, 128):
            end = min(row+128, y1-y0)
            sampled = bilinear_rgba(source, source_x[row:end]-x0, source_y[row:end]-y0)
            block = target[row:end]
            block[active[row:end]] = sampled[active[row:end]]
    return Image.fromarray(result)
