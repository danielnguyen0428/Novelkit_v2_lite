"""Hermes tool registry shim.

Self-registering tools call ``register(name, callable, *, schema=None)``
at import time. In a real Hermes deployment this proxies to
``hermes.tools.registry.register``; here we keep a process-local dict so the
package is verifiable in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

_REGISTRY: dict[str, "ToolEntry"] = {}


@dataclass(frozen=True)
class ToolEntry:
    name: str
    fn: Callable[..., Any]
    schema: Optional[dict] = None
    module: Optional[str] = None


def register(
    name: str,
    fn: Callable[..., Any],
    *,
    schema: Optional[dict] = None,
    module: Optional[str] = None,
    overwrite: bool = False,
) -> ToolEntry:
    if not overwrite and name in _REGISTRY:
        existing = _REGISTRY[name]
        if existing.fn is fn:
            return existing
        raise RuntimeError(
            f"Tool '{name}' already registered by {existing.module} "
            f"(set overwrite=True to replace)."
        )
    entry = ToolEntry(name=name, fn=fn, schema=schema, module=module)
    _REGISTRY[name] = entry
    return entry


def get(name: str) -> ToolEntry:
    return _REGISTRY[name]


def list_tools() -> list[str]:
    return sorted(_REGISTRY)


def reset() -> None:
    _REGISTRY.clear()
