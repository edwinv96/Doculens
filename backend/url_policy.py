from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable, Iterable
from urllib.parse import urlsplit, urlunsplit


AddressResolver = Callable[[str, int], Iterable[str]]


def _resolve_addresses(hostname: str, port: int) -> list[str]:
    return list(
        {
            item[4][0]
            for item in socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        }
    )


def validate_public_http_url(
    value: str,
    resolver: AddressResolver = _resolve_addresses,
) -> str:
    """Validate a URL before a server-side loader makes a network request."""
    parsed = urlsplit(value.strip())
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Only http and https URLs are supported.")
    if not parsed.hostname:
        raise ValueError("The URL must include a hostname.")
    if parsed.username or parsed.password:
        raise ValueError("Credentialed URLs are not supported.")
    if parsed.hostname.lower() == "localhost" or parsed.hostname.lower().endswith(".local"):
        raise ValueError("Local network hosts are not supported.")

    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise ValueError("The URL contains an invalid port.") from exc

    try:
        addresses = list(resolver(parsed.hostname, port))
    except OSError as exc:
        raise ValueError("The URL hostname could not be resolved.") from exc
    if not addresses:
        raise ValueError("The URL hostname did not resolve to an address.")

    for address in addresses:
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise ValueError("The URL resolved to an invalid IP address.") from exc
        if not ip.is_global:
            raise ValueError("Private, loopback, link-local, and reserved hosts are blocked.")

    return urlunsplit(parsed)

