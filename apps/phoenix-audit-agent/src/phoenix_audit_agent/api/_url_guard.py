"""SSRF guard for operator-supplied target URLs.

The auditor invokes whatever URL the operator submits, so the API boundary
must refuse URLs that aim the auditor at infrastructure instead of an agent:

- non-http(s) schemes and unparseable URLs (422 at POST, not mid-audit);
- the GCP metadata server + link-local range — blocked UNCONDITIONALLY;
- RFC1918 / IPv6 ULA / reserved / multicast / 0.0.0.0 — blocked
  UNCONDITIONALLY so attackers can't pivot to Cloud Run's VPC neighbors;
- userinfo (`user:pass@`) — rejected so embedded creds don't land in logs;
- loopback/localhost — blocked unless `environment=dev` or
  `ALLOW_LOCAL_TARGETS=true` (the local demo target runs on localhost:8001).

NB: DNS rebinding is NOT defended here — that requires a custom httpx
transport that pins the resolved IP. Tracked as follow-up; until then,
treat the guard as defense-in-depth, not sole protection.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlparse

from pydantic import AnyHttpUrl, TypeAdapter

from phoenix_audit_agent.config import get_settings

_HTTP_URL = TypeAdapter(AnyHttpUrl)

# Never legitimate audit targets, in any environment.
_METADATA_HOSTS = frozenset({"metadata.google.internal", "metadata"})
_LOOPBACK_HOSTS = frozenset({"localhost"})


def validate_target_url(raw: str) -> str:
    """Return `raw` unchanged if it is a safe http(s) target URL; raise ValueError."""
    _HTTP_URL.validate_python(raw)  # scheme + structural validity (pydantic ValueError)
    parsed = urlparse(raw)
    if parsed.username or parsed.password:
        # Userinfo in target URLs would leak basic-auth creds into structured
        # logs; reject upfront rather than try to scrub at log time.
        msg = "target_url must not contain embedded credentials"
        raise ValueError(msg)
    host = (parsed.hostname or "").lower()
    if not host:
        msg = f"target_url has no host: {raw!r}"
        raise ValueError(msg)

    if host in _METADATA_HOSTS:
        msg = "target_url must not point at the GCP metadata server"
        raise ValueError(msg)

    ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None

    if ip is not None:
        # `is_link_local` covers 169.254/16 incl. the raw-IP metadata server;
        # is_private covers RFC1918 + IPv6 ULA; is_reserved + is_multicast
        # + is_unspecified close 0.0.0.0 and the rest of the internal ranges.
        if ip.is_link_local:
            msg = "target_url must not point at a link-local address"
            raise ValueError(msg)
        # Loopback is intentionally excluded here — it has its own dev
        # carve-out below. Everything else (RFC1918, IPv6 ULA, multicast,
        # reserved, 0.0.0.0) is blocked unconditionally.
        if not ip.is_loopback and (
            ip.is_private or ip.is_reserved or ip.is_multicast or ip.is_unspecified
        ):
            msg = "target_url must not point at a private / reserved address"
            raise ValueError(msg)

    settings = get_settings()
    allow_local = settings.ALLOW_LOCAL_TARGETS or settings.environment == "dev"
    if not allow_local and (host in _LOOPBACK_HOSTS or (ip is not None and ip.is_loopback)):
        msg = (
            "target_url must not point at loopback outside dev "
            "(set ALLOW_LOCAL_TARGETS=true to override)"
        )
        raise ValueError(msg)
    return raw


__all__ = ["validate_target_url"]
