"""Face-anchored anime decals; uwu and blush are not enabled in the bot yet."""
import math

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

from .chudthor import OVAL
from .warpface import EYES, MOUTH

MODES = ("uwu", "blush", "sweat", "sparkle", "angry")


def apply_effect(image, detection, mode, pass_number=1):
    detection.require("face")
    if mode not in MODES:
        raise ValueError(mode)
    base = image.convert("RGBA").copy()
    if mode == "uwu":
        pixels = np.array(base)
        removal = np.zeros((image.height, image.width), np.uint8)
        for face in detection.faces:
            points = np.array([(p.x, p.y) for p in face], np.float32)
            for indices in (*EYES, MOUTH):
                feature = points[list(indices)]
                center = np.rint((feature.min(axis=0)+feature.max(axis=0))/2).astype(int)
                extent = np.maximum(3, (feature.max(axis=0)-feature.min(axis=0))/2+[3, 3])
                cv2.ellipse(removal, tuple(center), tuple(np.ceil(extent).astype(int)), 0, 0, 360, 255, -1)
        pixels[..., :3] = cv2.inpaint(pixels[..., :3].copy(), removal, 4, cv2.INPAINT_TELEA)
        base = Image.fromarray(pixels)
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
        if mode in {"uwu", "blush"}:
            cheeks = Image.new("RGBA", size)
            cheek_draw = ImageDraw.Draw(cheeks)
            for side in (-1, 1):
                cx, cy = position(side*.30, .12)
                rx, ry = width*.16*supersample, height*.075*supersample
                cheek_draw.ellipse((cx-rx, cy-ry, cx+rx, cy+ry), fill=(255, 95, 145, 80))
            cheeks = cheeks.filter(ImageFilter.GaussianBlur(max(1, width*.055*supersample)))
            overlay = Image.alpha_composite(overlay, cheeks)
            draw = ImageDraw.Draw(overlay)
        if mode == "uwu":
            # Literal U-w-U expression, replacing rather than covering features.
            ink = (65, 38, 45, 245)
            for indices in EYES:
                eye = np.array([(face[i].x, face[i].y) for i in indices])
                cx, cy = eye.mean(axis=0)*supersample
                radius = float(np.ptp(eye[:, 0]))*.48*supersample
                arc = [(cx+radius*math.cos(t), cy-radius*.22+radius*.48*math.sin(t))
                       for t in np.linspace(0, math.pi, 48)]
                draw.line(arc, fill=ink, width=stroke+1, joint="curve")
            mouth = np.array([(face[i].x, face[i].y) for i in MOUTH])
            mx, my = mouth.mean(axis=0)*supersample
            radius = width*.043*supersample
            for side in (-1, 1):
                cx = mx+side*radius*.65
                draw.arc((cx-radius, my-radius*.55, cx+radius, my+radius*.65),
                         0, 180, fill=ink, width=stroke)
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


