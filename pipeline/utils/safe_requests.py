"""
SSRF-hardened HTTP client for the void --news pipeline.

Wraps requests.Session with a custom HTTPAdapter that resolves the destination
hostname before each request (and after each redirect) and blocks any request
whose resolved IP falls inside a private, loopback, link-local, or multicast
range. This prevents a compromised RSS feed (or article URL) from coercing
the pipeline into reading cloud metadata endpoints (169.254.169.254),
loopback services, or RFC1918 internal services.

No new dependencies — uses stdlib `ipaddress` and `socket`.
"""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter


# Networks that must never be contacted via outbound HTTP.
# Each entry is parsed once at import time.
_BLOCKED_NETWORKS = [
    ipaddress.ip_network(cidr)
    for cidr in (
        # IPv4 — loopback, RFC1918 private, link-local (incl. cloud metadata),
        # CGNAT-adjacent zero, and multicast
        "127.0.0.0/8",     # loopback
        "10.0.0.0/8",      # RFC1918
        "172.16.0.0/12",   # RFC1918
        "192.168.0.0/16",  # RFC1918
        "169.254.0.0/16",  # link-local incl. 169.254.169.254 cloud metadata
        "0.0.0.0/8",       # "this network" — should never be a destination
        # IPv6 — loopback, ULA, link-local
        "::1/128",         # loopback
        "fc00::/7",        # unique local addresses
        "fe80::/10",       # link-local
    )
]


class BlockedAddressError(requests.exceptions.RequestException):
    """Raised when a request resolves to a blocked IP range (SSRF guard)."""


def _is_blocked_ip(ip_str: str) -> bool:
    """Return True if the given IP address falls inside any blocked range."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        # Unparseable — be safe and block.
        return True
    return any(ip in net for net in _BLOCKED_NETWORKS)


def _validate_host(host: str) -> None:
    """
    Resolve `host` and raise BlockedAddressError if any resolved address is
    in a blocked range. Resolves all addresses (A and AAAA) so that an
    attacker can't bypass the check by relying on a particular family.
    """
    if not host:
        raise BlockedAddressError("Empty host in request URL")

    # If the host is itself a literal IP, validate it directly.
    try:
        ipaddress.ip_address(host)
        if _is_blocked_ip(host):
            raise BlockedAddressError(f"Blocked IP literal: {host}")
        return
    except ValueError:
        pass  # not a literal — fall through to DNS resolution

    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        # DNS failure is an upstream concern, not an SSRF concern. Let the
        # connection attempt proceed so requests raises its normal error.
        raise BlockedAddressError(f"DNS resolution failed for {host}: {e}")

    for info in infos:
        sockaddr = info[4]
        ip_str = sockaddr[0]
        # Strip IPv6 zone identifier if present (e.g. "fe80::1%eth0")
        if "%" in ip_str:
            ip_str = ip_str.split("%", 1)[0]
        if _is_blocked_ip(ip_str):
            raise BlockedAddressError(
                f"Refusing to connect to {host}: resolves to blocked range ({ip_str})"
            )


class SSRFGuardAdapter(HTTPAdapter):
    """HTTPAdapter that validates the destination IP before each send.

    Because requests' Session re-invokes adapter.send() for each hop in a
    redirect chain, this also validates redirect targets — which is the
    primary attack vector for feed-driven SSRF.
    """

    def send(self, request, **kwargs):  # type: ignore[override]
        parsed = urlparse(request.url)
        _validate_host(parsed.hostname or "")
        return super().send(request, **kwargs)


def build_safe_session() -> requests.Session:
    """Return a requests.Session with SSRF guards mounted for http and https."""
    session = requests.Session()
    adapter = SSRFGuardAdapter()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


# Module-level singleton — cheap to share across threads since requests'
# Session is documented as thread-safe for typical GET workloads.
_SAFE_SESSION = build_safe_session()


def safe_get(url: str, **kwargs):
    """Drop-in replacement for requests.get that enforces SSRF blocking."""
    return _SAFE_SESSION.get(url, **kwargs)
