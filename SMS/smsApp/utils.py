"""Small shared helpers."""
import ipaddress

from django.conf import settings


def get_client_ip(request):
    """Return the client IP address as a string, or None if unavailable.

    X-Forwarded-For is only honoured when TRUSTED_PROXY_COUNT is greater than
    zero, and then only the entry added by the outermost trusted proxy is used,
    so clients cannot spoof their address.
    """
    if request is None:
        return None
    candidate = None
    proxy_count = getattr(settings, "TRUSTED_PROXY_COUNT", 0)
    if proxy_count > 0:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        parts = [part.strip() for part in forwarded.split(",") if part.strip()]
        if len(parts) >= proxy_count:
            candidate = parts[-proxy_count]
    if candidate is None:
        candidate = request.META.get("REMOTE_ADDR")
    if not candidate:
        return None
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None