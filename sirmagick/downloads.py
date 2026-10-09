"""Begrenzte HTTP-Downloads mit geprüften DNS-Ergebnissen und Weiterleitungen."""

import asyncio
import ipaddress
from pathlib import Path
import socket
from urllib.parse import urljoin, urlsplit


def public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
        if isinstance(address, ipaddress.IPv6Address) and address.ipv4_mapped:
            address = address.ipv4_mapped
        return address.is_global and not address.is_multicast
    except ValueError:
        return False


def validate_url(url: str) -> None:
    try:
        parsed = urlsplit(url)
        if parsed.scheme.lower() not in {"http", "https"} or not parsed.hostname:
            raise ValueError()
        if parsed.username is not None or parsed.password is not None:
            raise ValueError()
        if parsed.port not in {None, 80, 443}:
            raise ValueError()
        host = parsed.hostname.rstrip(".").lower()
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            raise ValueError()
        try:
            ipaddress.ip_address(host)
        except ValueError:
            return
        if not public_address(host):
            raise ValueError()
    except ValueError:
        raise ValueError("Die Bild-URL ist ungültig oder verweist auf ein internes Netzwerkziel.") from None


class PublicResolver:
    async def resolve(self, host, port=0, family=socket.AF_INET):
        loop = asyncio.get_running_loop()
        addresses = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM, family=family)
        if not addresses or any(not public_address(item[4][0]) for item in addresses):
            raise ValueError("Die Bildadresse verweist auf ein internes Netzwerkziel.")
        # Diese geprüften IPs verwendet direkt der Connector; keine zweite
        # DNS-Auflösung zwischen Sicherheitsprüfung und Verbindung.
        return [{"hostname": host, "host": item[4][0], "port": port,
                 "family": item[0], "proto": item[2], "flags": socket.AI_NUMERICHOST}
                for item in addresses]

    async def close(self):
        pass


def create_download_session(timeout: float):
    import aiohttp
    return aiohttp.ClientSession(
        connector=aiohttp.TCPConnector(resolver=PublicResolver(), use_dns_cache=False, limit=1),
        timeout=aiohttp.ClientTimeout(total=timeout), trust_env=False,
        auto_decompress=False, cookie_jar=aiohttp.DummyCookieJar(),
        headers={"User-Agent": "SirMagick/0.1", "Accept-Encoding": "identity"})


async def download_image(session, url: str, destination: Path, max_bytes: int, timeout: float):
    # Gesamtes Redirect-/Download-Budget, nicht ein neues Budget je Weiterleitung.
    try:
        async with asyncio.timeout(timeout):
            for _ in range(6):
                validate_url(url)
                async with session.get(url, allow_redirects=False) as response:
                    if response.status in {301, 302, 303, 307, 308}:
                        location = response.headers.get("Location")
                        if not location:
                            raise ValueError("Ungültige Weiterleitung beim Bilddownload.")
                        url = urljoin(url, location)
                        continue
                    if response.status != 200:
                        raise ValueError(f"Bilddownload fehlgeschlagen (HTTP {response.status}).")
                    if response.headers.get("Content-Encoding", "identity").lower() not in {"identity", ""}:
                        raise ValueError("Komprimierte HTTP-Antworten werden nicht unterstützt.")
                    if response.content_length is not None and response.content_length > max_bytes:
                        raise ValueError("Bilddownload überschreitet das Größenlimit.")
                    total = 0
                    with destination.open("wb") as output:
                        async for chunk in response.content.iter_chunked(64*1024):
                            total += len(chunk)
                            if total > max_bytes:
                                raise ValueError("Bilddownload überschreitet das Größenlimit.")
                            output.write(chunk)
                    if total == 0:
                        raise ValueError("Leere Bilddatei heruntergeladen.")
                    return
            raise ValueError("Zu viele Weiterleitungen beim Bilddownload.")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
