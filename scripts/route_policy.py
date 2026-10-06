"""Persistent user-approved provider quarantine, channel exceptions and ordering."""
from urllib.parse import urlsplit


def apply(name, routes, policy):
    denied = set(policy.get('blocked_route_urls', []))
    denied.update(policy.get('blocked_channel_routes', {}).get(name, []))
    hosts = set(policy.get('blocked_route_hosts', []))
    preferred = policy.get('preferred_routes', {}).get(name, [])
    result = []
    for url in list(preferred) + list(routes):
        if url not in denied and urlsplit(url).hostname not in hosts and url not in result:
            result.append(url)
    return result
