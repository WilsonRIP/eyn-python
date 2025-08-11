from __future__ import annotations

import urllib.robotparser as robotparser
from typing import Dict

import httpx


def fetch_robots_txt(base_url: str, timeout: float = 10.0) -> Dict[str, str | int]:
    # Basic downloader for robots.txt, returns text and status
    robots_url = base_url.rstrip("/") + "/robots.txt"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as c:
            r = c.get(robots_url)
            return {"url": robots_url, "status": r.status_code, "text": r.text}
    except Exception:
        return {"url": robots_url, "status": 0, "text": ""}


def can_fetch(base_url: str, user_agent: str, url: str, robots_text: str | None = None) -> bool:
    rp = robotparser.RobotFileParser()
    if robots_text is not None and robots_text.strip():
        rp.parse(robots_text.splitlines())
    else:
        robots_url = base_url.rstrip("/") + "/robots.txt"
        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as c:
                r = c.get(robots_url)
                if r.status_code == 200 and r.text:
                    rp.parse(r.text.splitlines())
                else:
                    rp.parse([])
        except Exception:
            rp.parse([])
    return rp.can_fetch(user_agent, url)


