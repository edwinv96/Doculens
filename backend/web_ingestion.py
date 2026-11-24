from __future__ import annotations

import os
from collections.abc import Callable
from urllib.parse import urljoin

import requests

try:
    from .url_policy import AddressResolver, validate_public_http_url
except ImportError:
    from url_policy import AddressResolver, validate_public_http_url


DEFAULT_MAX_WEB_BYTES = 2 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"text/html", "application/xhtml+xml", "text/plain"}
REDIRECT_CODES = {301, 302, 303, 307, 308}


def _max_response_bytes() -> int:
    try:
        value = int(os.getenv("MAX_WEB_BYTES", str(DEFAULT_MAX_WEB_BYTES)))
    except ValueError:
        return DEFAULT_MAX_WEB_BYTES
    return value if value > 0 else DEFAULT_MAX_WEB_BYTES


def fetch_public_page(
    url: str,
    *,
    request_get: Callable = requests.get,
    resolver: AddressResolver | None = None,
    max_bytes: int | None = None,
    max_redirects: int = 5,
) -> tuple[str, str, str]:
    """Fetch one bounded public page, validating every redirect before following it."""
    current_url = url
    limit = max_bytes if max_bytes is not None else _max_response_bytes()
    if limit <= 0:
        raise ValueError("The maximum web response size must be positive.")

    for redirect_number in range(max_redirects + 1):
        safe_url = (
            validate_public_http_url(current_url, resolver)
            if resolver is not None
            else validate_public_http_url(current_url)
        )
        response = request_get(
            safe_url,
            allow_redirects=False,
            stream=True,
            timeout=(5, 15),
            headers={"User-Agent": "DocuLens/1.0"},
        )
        try:
            if response.status_code in REDIRECT_CODES:
                location = response.headers.get("Location")
                if not location:
                    raise ValueError("The web page returned a redirect without a target.")
                if redirect_number >= max_redirects:
                    raise ValueError("The web page exceeded the redirect limit.")
                current_url = urljoin(safe_url, location)
                continue

            if not 200 <= response.status_code < 300:
                raise ValueError("The web page returned an unsuccessful HTTP status.")
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
            if content_type not in ALLOWED_CONTENT_TYPES:
                raise ValueError("Only HTML and plain-text web pages are supported.")

            declared_size = response.headers.get("Content-Length")
            if declared_size:
                try:
                    declared_bytes = int(declared_size)
                except ValueError:
                    declared_bytes = 0
                if declared_bytes > limit:
                    raise ValueError("The web page exceeded the configured response-size limit.")

            chunks: list[bytes] = []
            total = 0
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > limit:
                    raise ValueError("The web page exceeded the configured response-size limit.")
                chunks.append(chunk)
            body = b"".join(chunks).decode(response.encoding or "utf-8", errors="replace")
            return safe_url, content_type, body
        finally:
            response.close()

    raise ValueError("The web page could not be fetched safely.")
