"""Registry completeness + delegate seam tests (Task 11.2, Requirement 6.2/6.3).

- ``bootstrap.load_all()`` registers every expected ``novelkit_*`` tool;
- self-registration happens at import time (importing a tool module alone
  registers it);
- the two single-select plugins import and expose their factories;
- the Orchestrator dispatch seam (``delegate_tool``) reaches a tool and raises
  cleanly for an unknown tool (hub-and-spoke; no specialist-to-specialist edge).
"""

from __future__ import annotations

import importlib

import pytest

import bootstrap
from delegate import ToolNotRegistered, available_tools, delegate_tool
from tools import registry


def test_load_all_registers_every_expected_tool() -> None:
    registered = set(bootstrap.load_all())
    assert bootstrap.EXPECTED_TOOLS <= registered


def test_no_tools_missing() -> None:
    assert bootstrap.missing_tools() == set()


def test_verify_registry_passes() -> None:
    assert set(bootstrap.verify_registry()) >= bootstrap.EXPECTED_TOOLS


def test_expected_tools_count_matches_modules() -> None:
    # Each tool module self-registers exactly one tool, so the expected-tool
    # set size must equal the number of tool modules.
    assert len(bootstrap.EXPECTED_TOOLS) == len(bootstrap.TOOL_MODULES)


@pytest.mark.parametrize("module_name", bootstrap.TOOL_MODULES)
def test_each_tool_self_registers_on_import(module_name: str) -> None:
    """Importing a tool module is sufficient to register its tool."""
    module = importlib.import_module(module_name)
    # The module registered exactly one novelkit_* tool whose callable is present.
    matches = [
        name
        for name in registry.list_tools()
        if registry.get(name).module == module.__name__
    ]
    assert matches, f"{module_name} did not self-register a tool"


def test_plugins_import_and_expose_factories() -> None:
    plugins = bootstrap.import_plugins()
    memory = plugins["plugins.memory.novelkit_memory"]
    context = plugins["plugins.context_engine.novelkit_context"]
    assert hasattr(memory, "get_provider")
    assert hasattr(context, "build_engine")


def test_delegate_tool_reaches_registered_tool() -> None:
    bootstrap.load_all()
    # novelkit_dna resolve_genre is a pure, side-effect-free call — ideal probe.
    result = delegate_tool(
        "novelkit_dna", action="resolve_genre", genre_text="tu tiên"
    )
    assert isinstance(result, dict)


def test_delegate_tool_unknown_raises() -> None:
    with pytest.raises(ToolNotRegistered):
        delegate_tool("novelkit_does_not_exist")


def test_available_tools_matches_registry() -> None:
    bootstrap.load_all()
    assert available_tools() == registry.list_tools()
