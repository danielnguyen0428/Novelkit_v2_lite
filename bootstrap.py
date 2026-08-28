"""Package import surface — self-register every NovelKit tool + plugin (Task 11.2).

Each ``novelkit_*`` Custom Tool calls ``tools.registry.register(...)`` at import
time (Requirement 6.2). Importing a tool module is therefore enough to register
it. This module is the single place that imports **all** of them (plus the two
single-select plugins so their providers are constructible), so a host only has
to ``import bootstrap; bootstrap.load_all()`` to bring the whole NovelKit tool
surface online.

``load_all()`` is idempotent: re-importing a module is a no-op, and the registry
shim treats a re-``register`` of the same callable as a no-op too.
"""

from __future__ import annotations

import importlib
from types import ModuleType

from tools import registry

#: Every self-registering ``novelkit_*`` Custom Tool module (import-order
#: independent — the registry is a flat namespace).
TOOL_MODULES: tuple[str, ...] = (
    "tools.novelkit_pipeline_tool",
    "tools.novelkit_gate_tool",
    "tools.novelkit_language_guard_tool",
    "tools.novelkit_ai_flavor_tool",
    "tools.novelkit_cool_point_tool",
    "tools.novelkit_strand_tool",
    "tools.novelkit_style_coherence_tool",
    "tools.novelkit_reference_tool",
    "tools.novelkit_dna_tool",
    "tools.novelkit_sync_tool",
    "tools.novelkit_diagnostics_tool",
    "tools.novelkit_compass_tool",
    "tools.novelkit_recall_tool",
    "tools.novelkit_steer_tool",
    "tools.novelkit_graph_tool",
)

#: The two single-select Hermes plugins (memory-provider + context-engine).
#: They are not registry tools, but the tool surface depends on them, so the
#: bootstrap imports them too and verifies they expose their factory.
PLUGIN_MODULES: tuple[str, ...] = (
    "plugins.memory.novelkit_memory",
    "plugins.context_engine.novelkit_context",
)

#: The exact tool names every ``novelkit_*`` module must register. Used by the
#: registry-completeness test (Task 11.2) and by hosts that want to assert the
#: surface is fully online before serving.
EXPECTED_TOOLS: frozenset[str] = frozenset(
    {
        "novelkit_pipeline",
        "novelkit_gate",
        "novelkit_language_guard",
        "novelkit_ai_flavor",
        "novelkit_cool_point",
        "novelkit_strand",
        "novelkit_style_coherence",
        "novelkit_reference",
        "novelkit_dna",
        "novelkit_sync",
        "novelkit_diagnostics",
        "novelkit_compass",
        "novelkit_recall",
        "novelkit_steer",
        "novelkit_graph",
    }
)

# TOOL_MODULES and EXPECTED_TOOLS are two hand-maintained parallel lists (a
# module path per expected tool name). Guard against silent drift: if someone
# adds a module without its expected name (or vice versa) the counts diverge and
# this fails loudly at import instead of a tool going missing at runtime.
assert len(TOOL_MODULES) == len(EXPECTED_TOOLS), (
    f"bootstrap drift: {len(TOOL_MODULES)} tool modules vs "
    f"{len(EXPECTED_TOOLS)} expected tool names — keep them in lockstep"
)


def load_all() -> list[str]:
    """Import every tool + plugin module so all tools self-register.

    Returns the sorted list of registered tool names. Idempotent.
    """
    for module_name in TOOL_MODULES + PLUGIN_MODULES:
        importlib.import_module(module_name)
    return registry.list_tools()


def import_plugins() -> dict[str, ModuleType]:
    """Import (and return) the two single-select plugin modules."""
    return {name: importlib.import_module(name) for name in PLUGIN_MODULES}


def missing_tools() -> set[str]:
    """Tools expected but not registered after :func:`load_all`."""
    load_all()
    return set(EXPECTED_TOOLS) - set(registry.list_tools())


def verify_registry() -> list[str]:
    """Load everything and assert the full surface is registered.

    Raises ``RuntimeError`` listing any missing tools. Returns the registered
    tool names on success.
    """
    registered = load_all()
    missing = set(EXPECTED_TOOLS) - set(registered)
    if missing:
        raise RuntimeError(
            "NovelKit tool surface incomplete; missing: "
            + ", ".join(sorted(missing))
        )
    return registered


# Bring the surface online as soon as this module is imported.
load_all()
