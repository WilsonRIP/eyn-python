from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass
class RandomColorOptions:
    luminosity: str = "any"  # any|light|dark|pastel
    alpha: Optional[float] = None  # 0.0 - 1.0, when provided adds AA to #RRGGBB
    include_hash: bool = True
    seed: Optional[int] = None


def _hsl_to_rgb(h: float, s: float, l: float) -> tuple[int, int, int]:
    """Convert HSL (0-360, 0-1, 0-1) to RGB tuple (0-255).
    Implementation based on the algorithm from the CSS Color Module.
    """
    c = (1 - abs(2 * l - 1)) * s
    h_prime = (h % 360) / 60
    x = c * (1 - abs(h_prime % 2 - 1))

    r1 = g1 = b1 = 0.0
    if 0 <= h_prime < 1:
        r1, g1, b1 = c, x, 0
    elif 1 <= h_prime < 2:
        r1, g1, b1 = x, c, 0
    elif 2 <= h_prime < 3:
        r1, g1, b1 = 0, c, x
    elif 3 <= h_prime < 4:
        r1, g1, b1 = 0, x, c
    elif 4 <= h_prime < 5:
        r1, g1, b1 = x, 0, c
    else:  # 5 <= h_prime < 6
        r1, g1, b1 = c, 0, x

    m = l - c / 2
    r = int(round((r1 + m) * 255))
    g = int(round((g1 + m) * 255))
    b = int(round((b1 + m) * 255))
    return max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))


def _format_hex(r: int, g: int, b: int, alpha: Optional[float], include_hash: bool) -> str:
    prefix = "#" if include_hash else ""
    if alpha is None:
        return f"{prefix}{r:02X}{g:02X}{b:02X}"
    a = int(round(max(0.0, min(1.0, alpha)) * 255))
    return f"{prefix}{r:02X}{g:02X}{b:02X}{a:02X}"


def random_hex_color(
    luminosity: str = "any",
    alpha: Optional[float] = None,
    include_hash: bool = True,
    seed: Optional[int] = None,
) -> str:
    """Generate a random hex color.

    - luminosity: any|light|dark|pastel (biases HSL lightness/saturation)
    - alpha: optional 0..1 adds AA component → #RRGGBBAA
    - include_hash: prefix result with '#'
    - seed: if provided, produces deterministic color for the seed value
    """
    rng = random.Random(seed)

    h = rng.uniform(0, 360)
    if luminosity == "light":
        s = rng.uniform(0.4, 0.9)
        l = rng.uniform(0.7, 0.9)
    elif luminosity == "dark":
        s = rng.uniform(0.4, 0.9)
        l = rng.uniform(0.2, 0.35)
    elif luminosity == "pastel":
        s = rng.uniform(0.35, 0.6)
        l = rng.uniform(0.7, 0.85)
    else:  # any
        s = rng.uniform(0.25, 0.95)
        l = rng.uniform(0.35, 0.8)

    r, g, b = _hsl_to_rgb(h, s, l)
    return _format_hex(r, g, b, alpha, include_hash)


__all__ = ["RandomColorOptions", "random_hex_color"]


