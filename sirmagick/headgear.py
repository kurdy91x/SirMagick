"""Glowing halos and glossy curved horns anchored to each detected head."""
import math

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from .chudthor import OVAL

MODES = ("halo", "devilhorns")


def _curve(a, b, c, d):
    t = np.linspace(0, 1, 40)[:, None]
    return (1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d


def apply_effect(image, detection, mode):
    detection.require("face")
    if mode not in MODES:
        raise ValueError("Unknown headgear effect.")
    result = image.convert("RGBA").copy()
    for face in detection.faces:
        points = np.array([(p.x, p.y) for p in face])
        axis = points[263]-points[33]
        axis /= max(1e-6, float(np.linalg.norm(axis)))
        down = np.array([-axis[1], axis[0]])
        contour = points[list(OVAL)]
        width = max(10., float(np.ptp(contour @ axis)))
        height = max(10., float(np.ptp(contour @ down)))
        origin = points[10]
        # Render locally at bounded resolution, then rotate into image space.
        render = min(1600, max(128, round(width*3)))
        layer = Image.new("RGBA", (render, render))
        draw = ImageDraw.Draw(layer)
        scale = render/(width*2.4)
        def local(x, y):
            return np.array([render/2+x*width*scale, render*.58+y*height*scale])
        stroke = max(2, round(width*.015*scale))
        if mode == "halo":
            center = local(0, -.17)
            rx, ry = width*.52*scale, width*.12*scale
            for step in range(180):
                a, b = step*math.tau/180, (step+1)*math.tau/180
                color = (255, round(180+65*(.5+.5*math.sin(a))), round(35+115*(.5+.5*math.sin(a))), 245)
                segment = [(center[0]+rx*math.cos(t), center[1]+ry*math.sin(t)) for t in (a, b)]
                draw.line(segment, fill=color, width=stroke*3)
                draw.line([(x, y-stroke*.5) for x, y in segment], fill=(255, 250, 200, 245), width=stroke)
            for x, y, r in ((-.40, -.25, .055), (.35, -.12, .035)):
                p = local(x, y)
                span = width*r*scale
                draw.line((p[0]-span, p[1], p[0]+span, p[1]), fill=(255, 255, 225, 255), width=stroke)
                draw.line((p[0], p[1]-span, p[0], p[1]+span), fill=(255, 255, 225, 255), width=stroke)
        else:
            for side in (-1, 1):
                anchor = points[54 if side < 0 else 284]-origin
                desired = local(float(anchor @ axis)/width,
                                float(anchor @ down)/height-.025)
                base_center = local(side*.315, .10)
                def horn_point(x, y):
                    point = local(x, y)-base_center
                    point *= np.array([.85, .65])
                    return desired+point
                outer = _curve(horn_point(side*.40, .10), horn_point(side*.66, -.04),
                               horn_point(side*.64, -.33), horn_point(side*.43, -.43))
                inner = _curve(horn_point(side*.43, -.43), horn_point(side*.51, -.17),
                               horn_point(side*.27, -.08), horn_point(side*.23, .10))
                polygon = [tuple(p) for p in np.vstack((outer, inner))]
                draw.polygon(polygon, fill=(125, 8, 32, 255))
                # Nested highlights follow the curved horn, rather than flat triangles.
                for inset in range(5):
                    fraction = .10+inset*.11
                    middle = outer*(1-fraction)+inner[::-1]*fraction
                    draw.line([tuple(p) for p in middle], fill=(185+inset*14, 15+inset*10, 38+inset*8, 255),
                              width=max(1, stroke*2-inset//2), joint="curve")
                highlight = outer*.45+inner[::-1]*.55
                draw.line([tuple(p) for p in highlight[6:31]], fill=(255, 140, 130, 230), width=stroke, joint="curve")
                base = [tuple(horn_point(side*x, y)) for x, y in ((.40, .10), (.23, .10))]
                draw.line(base, fill=(65, 5, 25, 230), width=stroke*2)
        glow = layer.filter(ImageFilter.GaussianBlur(stroke*3))
        glow.putalpha(glow.getchannel("A").point(lambda a: round(a*.65)))
        layer = Image.alpha_composite(glow, layer)
        angle = -math.degrees(math.atan2(axis[1], axis[0]))
        # Keep rotation around the same anchor to preserve attachment to tilted heads.
        layer = layer.rotate(angle, resample=Image.Resampling.BICUBIC, center=(render/2, render*.58))
        size = max(1, round(render/scale))
        layer = layer.resize((size, size), Image.Resampling.LANCZOS)
        result.alpha_composite(layer, (round(origin[0]-size/2), round(origin[1]-size*.58)))
    result.putalpha(image.convert("RGBA").getchannel("A"))
    return result
