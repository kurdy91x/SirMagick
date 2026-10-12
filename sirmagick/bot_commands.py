from dataclasses import dataclass
import re
from urllib.parse import urlsplit

from .effects import EFFECTS


@dataclass(frozen=True)
class Command:
    effect: str
    url: str | None = None
    text: str | None = None


def parse_command(content: str, bot_id: int) -> Command | None:
    match = re.match(rf"^\s*(?:<@!?{bot_id}>|@sirmagick\b)\s*(.*?)\s*$", content,
                     re.DOTALL | re.IGNORECASE)
    if not match:
        return None
    parts = match.group(1).split()
    if not parts:
        return Command("help")
    effect = parts[0].lower()
    if effect not in EFFECTS | {"help"}:
        raise ValueError("Unknown command. Use @sirmagick help to list effects.")
    if effect == 'achievement':
        from .effect_options import achievement_parts
        words = parts[1:]
        url = None
        if words and urlsplit(words[-1].strip('<>')).scheme.lower() in {'http','https'}:
            url = words.pop().strip('<>')
        value = ' '.join(words)
        achievement_parts(value)
        return Command(effect,url,value)
    if len(parts) > 2 or (effect == "help" and len(parts) > 1):
        raise ValueError("Syntax: @SirMagick effect [image-url]")
    url = parts[1].strip("<>") if len(parts) == 2 else None
    if url and urlsplit(url).scheme.lower() not in {"http", "https"}:
        raise ValueError("Image URLs must start with http:// or https://.")
    return Command(effect, url)


def image_url(message, max_bytes: int) -> str | None:
    for attachment in message.attachments:
        content_type = attachment.content_type or ""
        suffix = urlsplit(attachment.filename).path.lower()
        if content_type.startswith("image/") or suffix.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            if attachment.size > max_bytes:
                raise ValueError("The selected image exceeds the download limit (25 MiB maximum, or the configured limit).")
            return attachment.url
    # Accept explicit image embeds, not arbitrary website preview thumbnails.
    for embed in message.embeds:
        if embed.type == "image" and embed.url:
            return embed.url
        if embed.image and embed.image.url:
            return embed.image.url
    for candidate in re.findall(r"https?://[^\s<>]+", message.content):
        if urlsplit(candidate).path.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            return candidate
    return None


async def find_image(message, limit: int, max_bytes: int) -> str:
    # Der aktuelle Anhang gewinnt. Ohne Anhang wird unmittelbar vor dem
    # Look for user commands; bot results are valid input images.
    found = image_url(message, max_bytes)
    if found:
        return found
    async for previous in message.channel.history(limit=limit, before=message, oldest_first=False):
        found = image_url(previous, max_bytes)
        if found:
            return found
    raise ValueError(f"No image found in the last {limit} messages.")
