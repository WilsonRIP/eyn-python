from __future__ import annotations

from typing import Protocol, Iterable
from importlib.metadata import entry_points

class EynPlugin(Protocol):
    name: str
    def register(self) -> None: ...

def load_plugins(group: str = "eyn_python.plugins") -> Iterable[EynPlugin]:
    eps = entry_points(group=group)
    for ep in eps:
        plugin = ep.load()
        if hasattr(plugin, "register"):
            yield plugin  # type: ignore[misc]


