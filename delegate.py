"""Orchestrator dispatch seam — ``delegate_tool`` (hub-and-spoke, Task 11.2).

The NovelKit Orchestrator (``Lãng Khách``) is a **hub**: specialists never call
each other directly (Requirement 6.3). Every cross-role call goes through this
one seam, which looks the target tool up in ``tools/registry.py`` and invokes
it. Modelling the dispatch here keeps the topology honest — there is exactly one
function the surface (CLI / gateway / cron) and the Orchestrator use to reach a
tool, so a specialist-to-specialist edge cannot exist by construction.

In a real Hermes deployment this maps onto Hermes' ``delegate_tool``; here it is
a thin registry call so the package is verifiable in isolation.
"""

from __future__ import annotations

from typing import Any

from tools import registry


class ToolNotRegistered(KeyError):
    """Raised when delegating to a tool that is not in the registry."""


def delegate_tool(tool_name: str, /, **kwargs: Any) -> Any:
    """Dispatch a call to a registered tool by name (the hub).

    Args:
        tool_name: the registered tool name (e.g. ``"novelkit_pipeline"``).
        **kwargs: keyword arguments forwarded to the tool entrypoint.

    Raises:
        ToolNotRegistered: when ``tool_name`` is not registered. Importing
            :mod:`bootstrap` first guarantees the full surface is online.
    """
    try:
        entry = registry.get(tool_name)
    except KeyError as exc:
        raise ToolNotRegistered(
            f"tool {tool_name!r} is not registered; "
            "import 'bootstrap' to bring the tool surface online"
        ) from exc
    return entry.fn(**kwargs)


def available_tools() -> list[str]:
    """List the tool names the Orchestrator can currently delegate to."""
    return registry.list_tools()
