"""SSRF guard: reject URLs that resolve to private/link-local/reserved space.

Resolve-then-check so a public hostname that maps to an internal IP is caught.
Hardened further in Phase 5; the core check lives here because the fetcher
needs it from day one.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


def _all_ips(host: str) -> list[str]:
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return []
    return [info[4][0] for info in infos]


def is_safe_url(url: str) -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False
    host = parsed.hostname
    if not host:
        return False

    ips = _all_ips(host)
    if not ips:
        return False

    for ip_str in ips:
        try:
            ip = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        ):
            return False
    return True
