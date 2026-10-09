"""Small hand-drawn meme stickers without external assets or fonts."""

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _smiley(laughing: bool) -> Image.Image:
    sticker = Image.new("RGBA", (256, 256))
    draw = ImageDraw.Draw(sticker)
    draw.ellipse((15, 15, 241, 241), fill="#ffdd00", outline="black", width=10)
    if laughing:
        for x in (78, 178):
            draw.line((x-21, 68, x+21, 106), fill="black", width=13)
            draw.line((x-21, 106, x+21, 68), fill="black", width=13)
    else:
        for x in (78, 178):
            draw.arc((x-25, 65, x+25, 108), 190, 350, fill="black", width=12)
        for x in (35, 204):
            draw.ellipse((x-12, 100, x+12, 155), fill="#00baff", outline="black", width=4)
    draw.ellipse((57, 120, 199, 217), fill="#440000", outline="black", width=9)
    draw.rectangle((77, 127, 179, 151), fill="white")
    draw.ellipse((100, 179, 174, 207), fill="#ff4260")
    return sticker


def _text(label: str) -> Image.Image:
    font = ImageFont.load_default(size=55)
    bbox = font.getbbox(label, stroke_width=5)
    width = bbox[2]-bbox[0]+35
    sticker = Image.new("RGBA", (width, 110))
    draw = ImageDraw.Draw(sticker)
    if label == "100%!!":
        center = (width/2, 55)
        points = []
        for i in range(28):
            angle = i*math.pi/14
            radius = 1 if i%2 == 0 else 0.72
            points.append((center[0]+math.cos(angle)*(width/2-3)*radius,
                           center[1]+math.sin(angle)*52*radius))
        draw.polygon(points, fill="#ffff00", outline="black", width=4)
    draw.text((17-bbox[0], 55-(bbox[1]+bbox[3])/2), label, font=font,
              fill="#ff2020" if label == "100%!!" else "white",
              stroke_width=5, stroke_fill="black")
    return sticker


def add_stickers(image: Image.Image, rng: np.random.Generator) -> Image.Image:
    if min(image.size) < 32:
        return image.copy()
    result = image.convert("RGBA")
    # Use different corners so the two stickers do not overlap.
    corners = rng.permutation(4)
    kinds = rng.choice(4, size=int(rng.integers(1, 3)), replace=False)
    for index, kind in enumerate(kinds):
        sticker = _smiley(kind == 0) if kind < 2 else _text("100%!!" if kind == 2 else "xD")
        max_size = max(14, round(min(image.size)*rng.uniform(0.15, 0.24)))
        if kind >= 2:
            max_size = round(max_size*1.65)
        sticker.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        sticker = sticker.rotate(float(rng.uniform(-19, 19)), Image.Resampling.BICUBIC, expand=True)
        sticker.thumbnail(image.size, Image.Resampling.LANCZOS)
        available_x, available_y = image.width-sticker.width, image.height-sticker.height
        jitter_x = round(available_x*rng.uniform(0.02, 0.13))
        jitter_y = round(available_y*rng.uniform(0.02, 0.13))
        corner = int(corners[index])
        x = jitter_x if corner%2 == 0 else available_x-jitter_x
        y = jitter_y if corner < 2 else available_y-jitter_y
        result.alpha_composite(sticker, (x, y))
    return result.convert("RGB")
