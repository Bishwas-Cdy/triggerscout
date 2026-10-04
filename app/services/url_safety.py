import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse


class UnsafeURLError(ValueError):
    pass


def normalize_page_url(base_url: str, page_url: str) -> str:
    candidate = urljoin(base_url, page_url)
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Only HTTP and HTTPS URLs are supported")
    if not parsed.hostname:
        raise UnsafeURLError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise UnsafeURLError("URLs containing credentials are not allowed")
    _reject_hostname(parsed.hostname)
    return candidate


def _reject_hostname(hostname: str) -> None:
    lowered = hostname.rstrip(".").lower()
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".localhost"):
        raise UnsafeURLError("Local URLs are not allowed")
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return
    if not address.is_global:
        raise UnsafeURLError("Private or non-global IP addresses are not allowed")


async def assert_public_url(url: str) -> str:
    safe_url = normalize_page_url(url, url)
    hostname = urlparse(safe_url).hostname
    assert hostname is not None
    try:
        records = await asyncio.to_thread(socket.getaddrinfo, hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError("Hostname could not be resolved") from exc
    if not records:
        raise UnsafeURLError("Hostname could not be resolved")
    for record in records:
        address = ipaddress.ip_address(record[4][0])
        if not address.is_global:
            raise UnsafeURLError("Hostname resolves to a private or non-global address")
    return safe_url
