from __future__ import annotations

import time
import ipaddress
import statistics
from typing import Dict, List, Optional, Sequence, Tuple, Literal, Any

import httpx


# -----------------------------
# Public IP detection
# -----------------------------

_IPV4_SERVICES: Tuple[str, ...] = (
    "https://api.ipify.org",
    "https://ipv4.icanhazip.com",
    "https://v4.ident.me",
    "https://ifconfig.me/ip",
)

_IPV6_SERVICES: Tuple[str, ...] = (
    "https://api64.ipify.org",
    "https://ipv6.icanhazip.com",
    "https://v6.ident.me",
    "https://ifconfig.co/ip",
)


def _is_global_ip(txt: str, family: Optional[Literal["ipv4", "ipv6"]] = None) -> Optional[str]:
    """Validate and return a cleaned global (public) IP string, else None."""
    s = (txt or "").strip()
    if not s:
        return None
    try:
        ip = ipaddress.ip_address(s)
        if family == "ipv4" and ip.version != 4:
            return None
        if family == "ipv6" and ip.version != 6:
            return None
        # Filter out non-global ranges
        if any((ip.is_private, ip.is_loopback, ip.is_link_local, ip.is_multicast, ip.is_reserved)):
            return None
        return str(ip)
    except Exception:
        return None


def _first_ip_from_services(
    services: Sequence[str],
    *,
    timeout: float,
    client: Optional[httpx.Client] = None,
    family: Optional[Literal["ipv4", "ipv6"]] = None,
) -> Optional[str]:
    close_client = client is None
    c = client or httpx.Client(http2=True, timeout=timeout, headers={"User-Agent": "EYN-Python/1.0"}, follow_redirects=True)
    try:
        for url in services:
            try:
                r = c.get(url)
                if r.status_code == 200:
                    ip = _is_global_ip(r.text, family=family)
                    if ip:
                        return ip
            except Exception:
                continue
        return None
    finally:
        if close_client:
            c.close()


def public_ips(*, timeout: float = 5.0) -> Dict[str, Optional[str]]:
    """
    Returns both IPv4 and IPv6 if available.
    {
      "ipv4": "203.0.113.10" | None,
      "ipv6": "2001:db8::1" | None
    }
    """
    with httpx.Client(http2=True, timeout=timeout, headers={"User-Agent": "EYN-Python/1.0"}, follow_redirects=True) as c:
        v4 = _first_ip_from_services(_IPV4_SERVICES, timeout=timeout, client=c, family="ipv4")
        v6 = _first_ip_from_services(_IPV6_SERVICES, timeout=timeout, client=c, family="ipv6")
    return {"ipv4": v4, "ipv6": v6}


def public_ip(*, timeout: float = 5.0, prefer_ipv6: bool = False) -> Dict[str, Optional[str]]:
    """
    Backward-compatible facade returning a single 'ip' key.
    Preference is IPv4 by default (common on dual-stack with no v6), or set prefer_ipv6=True.
    """
    ips = public_ips(timeout=timeout)
    chosen = ips["ipv6"] if prefer_ipv6 and ips["ipv6"] else ips["ipv4"] or ips["ipv6"]
    return {"ip": chosen}


# -----------------------------
# HTTP latency
# -----------------------------

def _measure_once(
    client: httpx.Client,
    url: str,
    method: Literal["GET", "HEAD"] = "GET",
) -> Dict[str, Any]:
    """
    Measures:
      - request_ms: until headers received (entering stream context)
      - ttfb_ms: until first response byte is read (GET only; for HEAD it's equal to request_ms)
    """
    sample: Dict[str, Any] = {"ok": False, "status": None, "request_ms": None, "ttfb_ms": None, "error": None}
    start = time.perf_counter()
    try:
        # Stream to separate headers/TTFB without downloading the full body.
        with client.stream(method, url) as r:
            # Time to headers (request/handshake/redirects complete)
            headers_ms = (time.perf_counter() - start) * 1000.0
            r.raise_for_status()
            sample["status"] = r.status_code
            sample["request_ms"] = round(headers_ms, 1)

            if method == "HEAD":
                # No body expected; treat TTFB same as headers
                sample["ttfb_ms"] = round(headers_ms, 1)
                sample["ok"] = True
                return sample

            # Pull first byte to approximate TTFB for GET
            first_byte_start = time.perf_counter()
            first_chunk = next(r.iter_bytes(), b"")
            ttfb_ms = (time.perf_counter() - start) * 1000.0 if first_chunk else headers_ms
            sample["ttfb_ms"] = round(ttfb_ms, 1)
            sample["ok"] = True
            return sample
    except Exception as exc:
        sample["error"] = f"{type(exc).__name__}: {exc}"
        return sample


def http_latency(
    url: str = "https://www.google.com",
    *,
    attempts: int = 3,
    timeout: float = 5.0,
    method: Literal["GET", "HEAD"] = "GET",
    follow_redirects: bool = True,
    verify: bool = True,
) -> Dict[str, object]:
    """
    Returns detailed per-attempt samples and summary stats.
    {
      "url": str,
      "method": "GET" | "HEAD",
      "attempts": int,
      "samples": [{"ok": bool, "status": int|None, "request_ms": float|None, "ttfb_ms": float|None, "error": str|None}, ...],
      "summary": {
        "ok": int, "fail": int,
        "request": {"min_ms":..., "max_ms":..., "avg_ms":..., "median_ms":..., "p90_ms":..., "stdev_ms":...},
        "ttfb": {"min_ms":..., "max_ms":..., "avg_ms":..., "median_ms":..., "p90_ms":..., "stdev_ms":...}
      }
    }
    """
    attempts = max(1, int(attempts))
    samples: List[Dict[str, Any]] = []

    # Single pooled client for consistent measurements.
    with httpx.Client(
        http2=True,
        timeout=timeout,
        headers={"User-Agent": "EYN-Python/1.0"},
        follow_redirects=follow_redirects,
        verify=verify,
    ) as client:
        for _ in range(attempts):
            samples.append(_measure_once(client, url, method))
            # Brief pause to avoid hammering too hard and to reduce server-driven caching artifacts
            time.sleep(0.05)

    def _stats(values: List[float]) -> Dict[str, Optional[float]]:
        if not values:
            return {"min_ms": None, "max_ms": None, "avg_ms": None, "median_ms": None, "p90_ms": None, "stdev_ms": None}
        values_sorted = sorted(values)
        n = len(values_sorted)
        p90 = values_sorted[min(n - 1, int(0.90 * (n - 1)))]
        return {
            "min_ms": round(values_sorted[0], 1),
            "max_ms": round(values_sorted[-1], 1),
            "avg_ms": round(sum(values_sorted) / n, 1),
            "median_ms": round(statistics.median(values_sorted), 1),
            "p90_ms": round(p90, 1),
            "stdev_ms": round(statistics.pstdev(values_sorted), 2) if n > 1 else 0.0,
        }

    req_vals = [s["request_ms"] for s in samples if s.get("request_ms") is not None]
    ttfb_vals = [s["ttfb_ms"] for s in samples if s.get("ttfb_ms") is not None]

    result: Dict[str, object] = {
        "url": url,
        "method": method,
        "attempts": attempts,
        "samples": samples,
        "summary": {
            "ok": sum(1 for s in samples if s["ok"]),
            "fail": sum(1 for s in samples if not s["ok"]),
            "request": _stats([float(v) for v in req_vals]),
            "ttfb": _stats([float(v) for v in ttfb_vals]),
        },
    }
    return result
