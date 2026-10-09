"""Adaptive colored glyph portraits using Pillow's bundled scalable font."""
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFont

MODES = ("numbers", "letters")


@lru_cache(maxsize=128)
def _font(size):
    # Bundled with Pillow; no Windows fonts, downloads, or system packages needed.
    return ImageFont.load_default(size=size)


def apply_effect(image, mode):
    if mode not in MODES:
        raise ValueError("Unknown typography effect.")
    original = image.convert("RGBA")
    width, height = image.size
    # Bound glyph analysis/rendering cost for large uploads, then restore size.
    render = original.copy()
    render.thumbnail((1600, 1600), Image.Resampling.LANCZOS)
    pixels = np.asarray(render, np.float32)
    w, h = render.size
    rgb = pixels[..., :3]
    alpha = pixels[..., 3]/255
    visible = rgb*alpha[..., None]
    gray = visible @ np.array([.2126, .7152, .0722], np.float32)
    canvas = Image.new("RGB", (w, h), (3, 5, 9))
    draw = ImageDraw.Draw(canvas)
    maximum = 2**round(np.log2(max(12, min(48, round(min(w, h)/25)))))
    max_font_size = max(2, round(round(maximum*.97)*.70))
    minimum = max(5, round(min(w, h)/110))
    alphabet = "0123456789" if mode == "numbers" else "ABCDEFGHIJKLMNOPQRSTUVWXYZ"

    def tile(x, y, size):
        x1, y1 = min(w, x+size), min(h, y+size)
        patch = gray[y:y1, x:x1]
        if not patch.size:
            return
        brightness = float(np.percentile(patch, 85))
        detail = float(patch.std())
        code = (x*73856093 ^ y*19349663 ^ size*83492791) & 0xFFFFFFFF
        if size >= minimum*2 and (detail > 16 or (brightness > 155 and code % 3 == 0)):
            half = size//2
            tile(x, y, half)
            tile(x+half, y, size-half)
            tile(x, y+half, size-half)
            tile(x+half, y+half, size-half)
            return
        weights = alpha[y:y1, x:x1]
        # Sample visible ink instead of dark glyph gaps during repeated passes.
        ink_weights = weights*(patch >= max(9., float(patch.max())*.45))
        if float(ink_weights.sum()) > .01:
            weights = ink_weights
            brightness = max(brightness, float(patch.max())*.8)
        total = float(weights.sum())
        if total < .01:
            return
        color = (rgb[y:y1, x:x1]*weights[..., None]).sum(axis=(0, 1))/total
        color = np.clip(color*1.55+12, 0, 255).astype(np.uint8)
        glyph = alphabet[(code+round(brightness)) % len(alphabet)]
        # Double the size spread while retaining the reduced maximum glyph size.
        size_factor = .27+.70*np.sqrt(brightness/255)
        font_size = min(max_font_size, max(2, round(min(x1-x, y1-y)*size_factor)))
        font = _font(font_size)
        stroke = 1 if font_size >= 16 else 0
        box = draw.textbbox((0, 0), glyph, font=font, stroke_width=stroke)
        gx = x+(x1-x-(box[2]-box[0]))/2-box[0]
        gy = y+(y1-y-(box[3]-box[1]))/2-box[1]
        draw.text((gx, gy), glyph, font=font, fill=tuple(int(c) for c in color),
                  stroke_width=stroke, stroke_fill=tuple(int(c) for c in color))

    for y in range(0, h, maximum):
        for x in range(0, w, maximum):
            tile(x, y, maximum)
    if canvas.size != (width, height):
        canvas = canvas.resize((width, height), Image.Resampling.LANCZOS)
    result = canvas.convert("RGBA")
    result.putalpha(original.getchannel("A"))
    return result
