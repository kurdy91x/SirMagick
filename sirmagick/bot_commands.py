from dataclasses import dataclass
import re
from urllib.parse import urlsplit

from .effects import EFFECTS


@dataclass(frozen=True)
class Command:
    effect: str
    url: str | None = None


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
        raise ValueError("Unbekannter Befehl. @sirmagick help zeigt alle Effekte.")
    if len(parts) > 2 or (effect == "help" and len(parts) > 1):
        raise ValueError("Syntax: @SirMagick effekt [bild-url]")
    url = parts[1].strip("<>") if len(parts) == 2 else None
    if url and urlsplit(url).scheme.lower() not in {"http", "https"}:
        raise ValueError("Bild-URLs müssen mit http:// oder https:// beginnen.")
    return Command(effect, url)


def image_url(message, max_bytes: int) -> str | None:
    for attachment in message.attachments:
        content_type = attachment.content_type or ""
        suffix = urlsplit(attachment.filename).path.lower()
        if content_type.startswith("image/") or suffix.endswith((".jpg", ".jpeg", ".png", ".webp", ".gif")):
            if attachment.size > max_bytes:
                raise ValueError("Das ausgewählte Bild ist zu groß (maximal 25 MiB oder konfiguriertes Limit).")
            return attachment.url
    # Nur explizite Bild-Embeds, keine beliebigen Website-Vorschaubilder.
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
    # Nutzerbefehl gesucht; Bot-Ergebnisse dürfen ausdrücklich Eingaben sein.
    found = image_url(message, max_bytes)
    if found:
        return found
    async for previous in message.channel.history(limit=limit, before=message, oldest_first=False):
        found = image_url(previous, max_bytes)
        if found:
            return found
    raise ValueError(f"Kein Bild in den letzten {limit} Nachrichten gefunden.")
