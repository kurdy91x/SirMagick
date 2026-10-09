"""Feste Deepfry-Rezeptur: Farbe, harte Kanten, Korn und echte JPEG-Artefakte."""

from hashlib import blake2b
from io import BytesIO

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps

MAX_WORK_SIDE = 1280


def _jpeg(image: Image.Image, quality: int) -> Image.Image:
    with BytesIO() as buffer:
        image.save(buffer, format="JPEG", quality=quality, subsampling=2)
        buffer.seek(0)
        with Image.open(buffer) as decoded:
            return decoded.convert("RGB")


def apply_deepfry(image: Image.Image, *, seed: int | None = None) -> Image.Image:
    """Ohne Gesichtserkennung; gleiche Abmessungen und unveränderter Alpha-Kanal.

    Rauschen folgt dem Bildinhalt, Sticker variieren pro Auftrag. Ein optionaler
    interner Seed ermöglicht reproduzierbare Tests, ohne Stärkeparameter im CLI.
    """
    rgba = image.convert("RGBA")
    alpha = rgba.getchannel("A")
    working = Image.new("RGB", rgba.size, "white")
    working.paste(rgba, mask=alpha)
    working.thumbnail((MAX_WORK_SIDE, MAX_WORK_SIDE), Image.Resampling.LANCZOS)
    noise_seed = int.from_bytes(blake2b(working.tobytes(), digest_size=8).digest(), "little")
    working = _jpeg(working, quality=30)
    working = ImageEnhance.Color(working).enhance(2.7)
    working = ImageEnhance.Contrast(working).enhance(1.65)
    working = working.filter(ImageFilter.UnsharpMask(radius=2.2, percent=320, threshold=1))
    # Warme, übersteuerte Mitteltöne; keine Emojis/Laseraugen oder Gesichtspflicht.
    pixels = np.asarray(working, dtype=np.float32)
    pixels = 255*np.power(pixels/255, 0.88)
    pixels *= np.array([1.10, 1.02, 0.84], np.float32)
    rng = np.random.default_rng(noise_seed)
    pixels += rng.normal(0, 7.0, (*pixels.shape[:2], 1)).astype(np.float32)
    working = Image.fromarray(np.clip(np.rint(pixels), 0, 255).astype(np.uint8))
    working = ImageOps.posterize(working, bits=6)
    from .stickers import add_stickers
    working = add_stickers(working, np.random.default_rng(seed))
    working = _jpeg(working, quality=14)
    if working.size != rgba.size:
        working = working.resize(rgba.size, Image.Resampling.BICUBIC)
    result = working.convert("RGBA")
    result.putalpha(alpha)
    return result
