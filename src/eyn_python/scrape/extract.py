from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

from selectolax.parser import HTMLParser


def _text(node) -> str:
    return node.text(strip=True) if node is not None else ""


def _attr(node, name: str) -> Optional[str]:
    return node.attributes.get(name) if node is not None else None


def _normalize_url(base: str, href: Optional[str]) -> Optional[str]:
    if not href or href.startswith("javascript:") or href.startswith("#"):
        return None
    return urljoin(base, href)


def extract_metadata(html: str, base_url: str) -> Dict[str, object]:
    tree = HTMLParser(html)

    title = _text(next(iter(tree.css("title")), None))
    lang = _attr(next(iter(tree.css("html")), None), "lang")
    meta_desc = _attr(next(iter(tree.css("meta[name='description']")), None), "content")
    meta_keywords = _attr(next(iter(tree.css("meta[name='keywords']")), None), "content")
    robots_meta = _attr(next(iter(tree.css("meta[name='robots']")), None), "content")
    canonical = _attr(next(iter(tree.css("link[rel='canonical']")), None), "href")
    canonical = _normalize_url(base_url, canonical) if canonical else None

    # OpenGraph
    og: Dict[str, str] = {}
    for m in tree.css("meta[property^='og:']"):
        prop = m.attributes.get("property")
        content = m.attributes.get("content")
        if prop and content:
            og[prop] = content

    # Twitter cards
    tw: Dict[str, str] = {}
    for m in tree.css("meta[name^='twitter:']"):
        name = m.attributes.get("name")
        content = m.attributes.get("content")
        if name and content:
            tw[name] = content

    # Headings counts
    headings = {f"h{i}": len(tree.css(f"h{i}")) for i in range(1, 7)}

    # Images summary
    imgs = tree.css("img[src]")
    img_urls: List[str] = []
    missing_alt = 0
    for n in imgs:
        u = _normalize_url(base_url, n.attributes.get("src"))
        if u:
            img_urls.append(u)
        if not n.attributes.get("alt"):
            missing_alt += 1

    # Text length (very rough)
    text_content = tree.body.text(separator=" ", strip=True) if tree.body else ""
    words = [w for w in text_content.split() if w]

    return {
        "title": title,
        "lang": lang,
        "description": meta_desc,
        "keywords": meta_keywords,
        "robots": robots_meta,
        "canonical": canonical,
        "opengraph": og,
        "twitter": tw,
        "headings": headings,
        "images": {
            "count": len(img_urls),
            "missing_alt": missing_alt,
            "samples": img_urls[:20],
        },
        "word_count": len(words),
    }


@dataclass(frozen=True)
class FormInput:
    name: Optional[str]
    type: Optional[str]
    value: Optional[str]


@dataclass(frozen=True)
class Form:
    method: str
    action: str
    inputs: List[FormInput]


def extract_forms(html: str, base_url: str) -> List[Dict[str, object]]:
    tree = HTMLParser(html)
    results: List[Dict[str, object]] = []
    for f in tree.css("form"):
        method = (f.attributes.get("method") or "get").lower()
        action_rel = f.attributes.get("action") or base_url
        action = _normalize_url(base_url, action_rel) or base_url
        inputs: List[FormInput] = []
        for inp in f.css("input"):
            inputs.append(
                FormInput(
                    name=inp.attributes.get("name"),
                    type=inp.attributes.get("type"),
                    value=inp.attributes.get("value"),
                )
            )
        results.append({
            "method": method,
            "action": action,
            "inputs": [asdict(i) for i in inputs],
        })
    return results


def extract_assets(html: str, base_url: str) -> Dict[str, List[str]]:
    tree = HTMLParser(html)
    imgs = []
    for n in tree.css("img[src]"):
        u = _normalize_url(base_url, n.attributes.get("src"))
        if u:
            imgs.append(u)
    js = []
    for s in tree.css("script[src]"):
        u = _normalize_url(base_url, s.attributes.get("src"))
        if u:
            js.append(u)
    css = []
    for l in tree.css("link[rel='stylesheet'][href]"):
        u = _normalize_url(base_url, l.attributes.get("href"))
        if u:
            css.append(u)
    media = []
    for v in tree.css("video[src],audio[src],source[src]"):
        u = _normalize_url(base_url, v.attributes.get("src"))
        if u:
            media.append(u)
    return {
        "images": imgs,
        "scripts": js,
        "styles": css,
        "media": media,
    }


