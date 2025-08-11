from __future__ import annotations

import re
from typing import Iterator, List

import httpx

SITEMAP_RE = re.compile(r"<loc>\s*(?P<url>[^<]+)\s*</loc>", re.IGNORECASE)


def fetch_sitemap_urls(base_url: str, timeout: float = 20.0) -> List[str]:
    """Fetch sitemap.xml (or /sitemap_index.xml) and return list of URLs.

    Tries /sitemap.xml then /sitemap_index.xml. Parses basic XML without heavy deps.
    """
    candidates = [
        base_url.rstrip("/") + "/sitemap.xml",
        base_url.rstrip("/") + "/sitemap_index.xml",
    ]
    urls: list[str] = []
    with httpx.Client(timeout=timeout, follow_redirects=True) as c:
        for url in candidates:
            try:
                r = c.get(url)
                if r.status_code != 200 or not r.text:
                    continue
                urls.extend([m.group("url").strip() for m in SITEMAP_RE.finditer(r.text)])
            except Exception:
                continue
    # Deduplicate preserving order
    seen: set[str] = set()
    uniq: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


