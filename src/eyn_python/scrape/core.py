from __future__ import annotations

import re
import time
import asyncio
import random
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, Iterator, Optional, Sequence, Set, Tuple, Pattern
from urllib.parse import urljoin, urlparse, urlunparse
import urllib.robotparser as robotparser

import httpx
from selectolax.parser import HTMLParser

from eyn_python.logging import get_logger

log = get_logger(__name__)


@dataclass
class HttpClient:
    timeout: float = 20.0
    retries: int = 2
    backoff: float = 0.75
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    def get(self, url: str) -> str:
        headers = {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"}
        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                with httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True) as c:
                    r = c.get(url)
                    r.raise_for_status()
                    return r.text
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self.retries:
                    sleep_s = self.backoff * (2 ** attempt)
                    log.debug(f"GET failed (attempt {attempt+1}), retrying in {sleep_s:.2f}s...")
                    time.sleep(sleep_s)
        assert last_exc is not None
        raise last_exc

    def get_headers(self, url: str) -> Dict[str, str]:
        headers = {"User-Agent": self.user_agent}
        with httpx.Client(timeout=self.timeout, headers=headers, follow_redirects=True) as c:
            r = c.head(url)
            r.raise_for_status()
            return dict(r.headers)


def parse_html(html: str) -> HTMLParser:
    return HTMLParser(html)


def extract_all(
    tree: HTMLParser,
    selectors: Dict[str, str],
    attr: Optional[str] = None,
) -> Dict[str, list[str]]:
    results: Dict[str, list[str]] = {}
    for key, sel in selectors.items():
        items: list[str] = []
        for n in tree.css(sel):
            if attr:
                val = n.attributes.get(attr)
                if val:
                    items.append(val)
            else:
                items.append(n.text(strip=True))
        results[key] = items
    return results


def _same_domain(a: str, b: str) -> bool:
    return urlparse(a).netloc == urlparse(b).netloc


def _normalize_url(base: str, href: str) -> Optional[str]:
    if not href or href.startswith("javascript:") or href.startswith("#"):
        return None
    return urljoin(base, href)


def crawl(
    start_url: str,
    max_pages: int = 20,
    same_domain: bool = True,
    should_visit: Optional[Callable[[str], bool]] = None,
) -> Iterator[tuple[str, str]]:
    """Simple breadth-first crawler yielding (url, html).

    - Respects same-domain restriction when enabled.
    - No robots.txt or politeness here; for production, integrate better controls.
    """
    client = HttpClient()
    visited: Set[str] = set()
    queue: list[str] = [start_url]

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        if same_domain and not _same_domain(start_url, url):
            continue
        if should_visit and not should_visit(url):
            continue

        try:
            html = client.get(url)
        except Exception as exc:  # noqa: BLE001
            log.debug(f"Skip {url}: {exc}")
            continue

        visited.add(url)
        yield url, html

        tree = parse_html(html)
        for a in tree.css("a[href]"):
            href = a.attributes.get("href")
            nxt = _normalize_url(url, href) if href else None
            if nxt and nxt not in visited:
                queue.append(nxt)


# ---------------- Advanced async crawling ----------------


def _origin(url: str) -> str:
    p = urlparse(url)
    return urlunparse((p.scheme, p.netloc, "", "", "", ""))


class RobotsCache:
    def __init__(self, user_agent: str) -> None:
        self._user_agent = user_agent
        self._cache: Dict[str, robotparser.RobotFileParser] = {}

    async def fetch(self, client: httpx.AsyncClient, base_url: str) -> robotparser.RobotFileParser:
        origin = _origin(base_url)
        if origin in self._cache:
            return self._cache[origin]
        rp = robotparser.RobotFileParser()
        robots_url = origin.rstrip("/") + "/robots.txt"
        try:
            r = await client.get(robots_url)
            if r.status_code == 200 and r.text:
                rp.parse(r.text.splitlines())
            else:
                rp.parse([])
        except Exception:  # noqa: BLE001
            rp.parse([])
        self._cache[origin] = rp
        return rp

    async def allowed(self, client: httpx.AsyncClient, url: str) -> bool:
        rp = await self.fetch(client, url)
        return rp.can_fetch(self._user_agent, url)


@dataclass
class AsyncHttpClient:
    timeout: float = 20.0
    retries: int = 2
    backoff: float = 0.75
    user_agent: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )

    def _headers(self) -> Dict[str, str]:
        return {"User-Agent": self.user_agent, "Accept": "text/html,application/xhtml+xml"}

    async def get(self, client: httpx.AsyncClient, url: str) -> str:
        last_exc: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                r = await client.get(url)
                if r.status_code in (429, 500, 502, 503, 504):
                    raise httpx.HTTPStatusError("retryable status", request=r.request, response=r)
                r.raise_for_status()
                return r.text
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self.retries:
                    retry_after = 0.0
                    if isinstance(exc, httpx.HTTPStatusError):
                        ra = exc.response.headers.get("Retry-After")
                        if ra:
                            try:
                                retry_after = float(ra)
                            except Exception:
                                retry_after = 0.0
                    sleep_s = retry_after or (self.backoff * (2 ** attempt) * (1 + random.random() * 0.25))
                    await asyncio.sleep(sleep_s)
        assert last_exc is not None
        raise last_exc


async def crawl_async(
    start_url: str,
    *,
    max_pages: int = 20,
    concurrency: int = 5,
    delay: float = 0.5,
    same_domain: bool = True,
    obey_robots: bool = True,
    user_agent: Optional[str] = None,
    should_visit: Optional[Callable[[str], bool]] = None,
) -> Sequence[Tuple[str, str]]:
    """Concurrent crawler returning a list of (url, html)."""
    ua = user_agent or (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    )
    ahc = AsyncHttpClient(user_agent=ua)
    robots = RobotsCache(user_agent=ua)

    visited: Set[str] = set()
    results: list[Tuple[str, str]] = []
    queue: asyncio.Queue[str] = asyncio.Queue()
    await queue.put(start_url)

    sem = asyncio.Semaphore(max(1, concurrency))
    last_fetch: Dict[str, float] = {}

    async with httpx.AsyncClient(timeout=ahc.timeout, headers=ahc._headers(), http2=True, follow_redirects=True) as client:
        async def worker() -> None:
            nonlocal results
            while len(results) < max_pages:
                try:
                    url = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    return
                if url in visited:
                    queue.task_done()
                    continue
                if same_domain and not _same_domain(start_url, url):
                    queue.task_done()
                    continue
                if should_visit and not should_visit(url):
                    queue.task_done()
                    continue

                origin = _origin(url)
                # Politeness: simple per-origin delay
                now = asyncio.get_event_loop().time()
                last = last_fetch.get(origin, 0.0)
                wait_for = max(0.0, (last + delay) - now)
                if wait_for > 0:
                    await asyncio.sleep(wait_for)

                # robots.txt
                if obey_robots:
                    allowed = await robots.allowed(client, url)
                    if not allowed:
                        queue.task_done()
                        continue

                async with sem:
                    try:
                        html = await ahc.get(client, url)
                    except Exception:
                        queue.task_done()
                        continue

                last_fetch[origin] = asyncio.get_event_loop().time()
                visited.add(url)
                results.append((url, html))
                queue.task_done()

                # Enqueue new links
                tree = parse_html(html)
                for a in tree.css("a[href]"):
                    href = a.attributes.get("href")
                    nxt = _normalize_url(url, href) if href else None
                    if nxt and nxt not in visited and queue.qsize() < max_pages * 4:
                        await queue.put(nxt)

        tasks = [asyncio.create_task(worker()) for _ in range(max(1, concurrency))]
        await asyncio.gather(*tasks)

    return results


def extract_links(html: str, base_url: str) -> list[str]:
    tree = parse_html(html)
    links: list[str] = []
    for a in tree.css("a[href]"):
        href = a.attributes.get("href")
        url = _normalize_url(base_url, href) if href else None
        if url:
            links.append(url)
    # Deduplicate preserving order
    seen: Set[str] = set()
    uniq: list[str] = []
    for u in links:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq


def _build_pattern(keyword: str, *, regex: bool, ignore_case: bool, whole_word: bool) -> Pattern[str]:
    flags = re.IGNORECASE if ignore_case else 0
    if regex:
        return re.compile(keyword, flags)
    escaped = re.escape(keyword)
    if whole_word:
        return re.compile(rf"\b{escaped}\b", flags)
    return re.compile(escaped, flags)


async def search_async(
    start_url: str,
    keywords: Sequence[str],
    *,
    max_pages: int = 50,
    concurrency: int = 6,
    delay: float = 0.4,
    same_domain: bool = True,
    obey_robots: bool = True,
    user_agent: Optional[str] = None,
    ignore_case: bool = True,
    regex: bool = False,
    whole_word: bool = False,
) -> list[Tuple[str, Dict[str, int]]]:
    """Crawl and return pages containing any of the keywords with match counts.

    Returns a list of (url, {keyword: count, ...}) for pages with >=1 match.
    """
    if not keywords:
        return []

    patterns = [(kw, _build_pattern(kw, regex=regex, ignore_case=ignore_case, whole_word=whole_word)) for kw in keywords]
    pages = await crawl_async(
        start_url,
        max_pages=max_pages,
        concurrency=concurrency,
        delay=delay,
        same_domain=same_domain,
        obey_robots=obey_robots,
        user_agent=user_agent,
    )
    hits: list[Tuple[str, Dict[str, int]]] = []
    for url, html in pages:
        counts: Dict[str, int] = {}
        for kw, pat in patterns:
            n = len(pat.findall(html)) if html else 0
            if n:
                counts[kw] = n
        if counts:
            hits.append((url, counts))
    return hits


