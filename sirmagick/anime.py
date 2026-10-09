"""Face-anchored anime effects that retain the original facial texture."""
import math

import numpy as np
import cv2
from PIL import Image, ImageDraw

from .chudthor import OVAL
from .warpface import EYES, MOUTH

MODES = ("uwu", "blush", "sweat", "sparkle", "angry")


def _cute_face(image, detection, mode):
    """Use local feature scaling and translucent cheek color, without inpainting."""
    from .face_modes import local_scale

    original = np.array(image.convert("RGBA"))
    pixels = original.copy()
    if mode == "uwu":
        for face in detection.faces:
            points = np.array([(p.x, p.y) for p in face], dtype=np.float32)
            for indices in EYES:
                local_scale(pixels, points[list(indices)], 1.20, outer=2.0,
                            padding=(1.15, 1.5))
            local_scale(pixels, points[list(MOUTH)], .78, outer=1.8,
                        padding=(1.15, 1.4))

    for face in detection.faces:
        points = np.array([(p.x, p.y) for p in face], dtype=np.float32)
        contour = points[list(OVAL)]
        eye_axis = points[263]-points[33]
        eye_axis /= max(float(np.linalg.norm(eye_axis)), 1e-6)
        down = np.array([-eye_axis[1], eye_axis[0]])
        width = max(10., float(np.ptp(contour @ eye_axis)))
        height = max(10., float(np.ptp(contour @ down)))
        low = np.maximum(0, np.floor(contour.min(axis=0))).astype(int)
        high = np.minimum([image.width, image.height], np.ceil(contour.max(axis=0)+1)).astype(int)
        x0, y0 = low
        x1, y1 = high
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        mask = np.zeros((y1-y0, x1-x0), np.uint8)
        cv2.fillConvexPoly(mask, cv2.convexHull(np.rint(contour).astype(np.int32)-low), 255)
        # Keep the eyes, nose, and lips free of cheek color and hatch marks.
        from .warpface import NOSE
        for indices in (*EYES, NOSE, MOUTH):
            cv2.fillConvexPoly(mask, cv2.convexHull(np.rint(points[list(indices)]).astype(np.int32)-low), 0)
        strength = np.zeros(mask.shape, np.float32)
        hatches = np.zeros(mask.shape, np.uint8)
        for eye, lip, side in ((33, 61, -1), (263, 291, 1)):
            center = points[eye]*.48+points[lip]*.52+eye_axis*side*width*.035
            dx, dy = xx-center[0], yy-center[1]
            u, v = dx*eye_axis[0]+dy*eye_axis[1], dx*down[0]+dy*down[1]
            strength = np.maximum(strength, np.exp(-.5*((u/(width*.105))**2+(v/(height*.045))**2)))
            for shift in (-.035, 0, .035):
                mid = center+eye_axis*width*shift
                delta = eye_axis*width*.010-down*height*.023
                a = tuple(np.rint(mid-delta-low).astype(int))
                b = tuple(np.rint(mid+delta-low).astype(int))
                cv2.line(hatches, a, b, 255, max(1, round(width*.006)), cv2.LINE_AA)
        feather = np.clip(cv2.distanceTransform(mask, cv2.DIST_L2, 3)/max(1., width*.025), 0, 1)
        strength *= feather
        target = pixels[y0:y1, x0:x1, :3].astype(np.float32)
        # Tint existing pixels rather than painting flat patches over skin.
        pink = np.array([1.0, .28, .48], np.float32)
        luminance = target.max(axis=2, keepdims=True)
        tint = np.maximum(target, luminance*.9)*pink
        amount = (.30*strength + .26*(hatches/255)*feather)[..., None]
        pixels[y0:y1, x0:x1, :3] = np.clip(target*(1-amount)+tint*amount, 0, 255).astype(np.uint8)
    pixels[..., 3] = original[..., 3]
    return Image.fromarray(pixels)


def apply_effect(image, detection, mode, pass_number=1):
    detection.require("face")
    if mode not in MODES:
        raise ValueError(mode)
    if mode in {"uwu", "blush"}:
        return _cute_face(image, detection, mode)
    base = image.convert("RGBA").copy()
    # Draw at double resolution for clean decal edges.
    supersample = 2
    size = (base.width*supersample, base.height*supersample)
    overlay = Image.new("RGBA", size)
    draw = ImageDraw.Draw(overlay)
    for face in detection.faces:
        outline = np.array([(face[i].x, face[i].y) for i in OVAL])
        center = (outline.min(axis=0)+outline.max(axis=0))/2
        width = float(max(10, np.ptp(outline[:, 0])))
        height = float(max(10, np.ptp(outline[:, 1])))
        angle = math.atan2(face[263].y-face[33].y, face[263].x-face[33].x)
        def position(x, y):
            dx, dy = x*width, y*height
            return ((center[0]+dx*math.cos(angle)-dy*math.sin(angle))*supersample,
                    (center[1]+dx*math.sin(angle)+dy*math.cos(angle))*supersample)
        stroke = max(2, round(width*.012*supersample))
        if mode == "sweat":
            # Different side on the next pass makes the second drop accumulate.
            side = 1 if pass_number % 2 else -1
            cx, cy = position(side*.48, -.24)
            rw, rh = width*.065*supersample, height*.15*supersample
            points = [(cx, cy-rh)]
            points += [(cx+rw*math.cos(a), cy+rh*.1+rh*.55*math.sin(a))
                       for a in np.linspace(-.40, math.pi+.40, 60)]
            points.append((cx, cy-rh))
            draw.polygon(points, fill=(70, 195, 255, 235))
            draw.line(points, fill=(20, 95, 155, 255), width=stroke, joint="curve")
            draw.ellipse((cx-rw*.45, cy-rh*.1, cx-rw*.05, cy+rh*.2), fill=(230, 255, 255, 255))
        if mode == "sparkle":
            shift = .035*(pass_number-1)
            for x, y, scale in ((-.54, -.15, 1), (.51, -.36, .8), (.45, .30, .6), (-.35, -.55, .55)):
                cx, cy = position(x+shift, y-shift)
                radius = width*.09*supersample*scale
                polygon = []
                for index in range(8):
                    a = index*math.pi/4
                    r = radius if index % 2 == 0 else radius*.22
                    polygon.append((cx+math.cos(a)*r, cy+math.sin(a)*r))
                draw.polygon(polygon, fill=(255, 235, 95, 250))
                draw.line(polygon+[polygon[0]], fill=(255, 255, 235, 255), width=stroke)
        if mode == "angry":
            cx, cy = position(.34 if pass_number % 2 else -.34, -.40)
            r = width*.065*supersample
            for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
                points = [(cx+sx*r, cy+sy*r*.25), (cx+sx*r*.48, cy+sy*r*.48),
                          (cx+sx*r*.25, cy+sy*r)]
                draw.line(points, fill=(255, 245, 245, 255), width=stroke*3, joint="curve")
                draw.line(points, fill=(245, 45, 65, 255), width=stroke*2, joint="curve")
    overlay = overlay.resize(base.size, Image.Resampling.LANCZOS)
    result = Image.alpha_composite(base, overlay)
    result.putalpha(image.convert("RGBA").getchannel("A"))
    return result


