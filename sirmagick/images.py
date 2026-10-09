from pathlib import Path
import warnings

from PIL import Image, ImageOps, UnidentifiedImageError

from .data import ImageError

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 24_000_000


def image_paths(source: Path) -> list[Path]:
    if source.is_file():
        if source.suffix.lower() not in EXTENSIONS:
            raise ImageError(f"Unsupported file extension: {source.suffix}")
        return [source]
    if not source.is_dir():
        raise ImageError(f"Input does not exist: {source}")
    return sorted(p for p in source.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONS)


def load_image(path: Path) -> Image.Image:
    if path.stat().st_size > MAX_BYTES:
        raise ImageError("Image exceeds 25 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as source:
                if source.format not in {"JPEG", "PNG", "WEBP", "GIF"}:
                    raise ImageError("Unsupported image content.")
                if source.width * source.height > MAX_PIXELS:
                    raise ImageError("Image exceeds 24 million pixels.")
                source.seek(0)
                return ImageOps.exif_transpose(source).convert("RGBA")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError,
            Image.DecompressionBombWarning) as exc:
        raise ImageError(f"Cannot read image: {exc}") from exc


def detection_image(image: Image.Image, max_side: int) -> Image.Image:
    # Composite transparency over white; keep the original unchanged for effects.
    rgb = Image.new("RGB", image.size, "white")
    rgb.paste(image, mask=image.getchannel("A"))
    rgb.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    return rgb
