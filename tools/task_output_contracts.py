"""Shared task output contracts for dispatch, verification, and readiness.

Ported verbatim (semantics-preserving) from the legacy
``_novelkit_source/scripts/task_output_contracts.py`` as part of Task 5.3
(handling finding D7). This module is the single schema source for the
input/output paths of every pipeline task: the pipeline tool uses it to attach
``required`` / ``writable`` / ``readiness`` path sets to each ``Task`` so that
Hermes can verify a task's outputs deterministically.

Keeping this as a standalone module (rather than inlining it) preserves the
legacy contract: callers and tests import ``output_contract_for_task`` and the
``BOOTSTRAP_OUTPUT_CONTRACTS`` table exactly as before.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OutputContract:
    required_paths: tuple[str, ...] = ()
    writable_paths: tuple[str, ...] = ()
    readiness_paths: tuple[str, ...] = ()
    optional_paths: tuple[str, ...] = ()

    @property
    def readiness_index_path(self) -> str | None:
        return self.readiness_paths[0] if self.readiness_paths else None


BOOTSTRAP_OUTPUT_CONTRACTS: dict[str, OutputContract] = {
    "bootstrap.characters": OutputContract(
        required_paths=("database/characters/",),
        writable_paths=("database/characters/",),
        readiness_paths=("database/characters/",),
    ),
    "bootstrap.world": OutputContract(
        required_paths=(
            "database/worldbuilding/WorldOverview.md",
            "database/systems/cultivation.md",
            "database/systems/world_rules.md",
        ),
        writable_paths=(
            "database/worldbuilding/WorldOverview.md",
            "database/worldbuilding/geography.md",
            "database/worldbuilding/factions.md",
            "database/systems/cultivation.md",
            "database/systems/world_rules.md",
        ),
        readiness_paths=("database/worldbuilding/WorldOverview.md",),
    ),
    "bootstrap.plot_threads": OutputContract(
        required_paths=(
            "database/plot_threads/threads_master.md",
            "database/plot_threads/seeds_tracker.md",
        ),
        writable_paths=(
            "database/plot_threads/threads_master.md",
            "database/plot_threads/seeds_tracker.md",
        ),
        readiness_paths=(
            "database/plot_threads/threads_master.md",
            "database/plot_threads/seeds_tracker.md",
        ),
    ),
    "bootstrap.timeline": OutputContract(
        required_paths=("database/timeline/master_timeline.md",),
        writable_paths=("database/timeline/master_timeline.md",),
        readiness_paths=("database/timeline/master_timeline.md",),
    ),
    "bootstrap.master_outline": OutputContract(
        required_paths=("outlines/master_outline.md",),
        writable_paths=("outlines/master_outline.md",),
        readiness_paths=("outlines/master_outline.md",),
    ),
}


def output_contract_for_task(task: "dict | object") -> OutputContract:
    """Return the :class:`OutputContract` for ``task``.

    Accepts either a plain ``dict`` (legacy call shape) or any object exposing
    ``task_key`` / ``output_paths`` attributes (the new ``Task`` dataclass).
    Bootstrap tasks have hand-authored contracts; every other task derives its
    contract from its declared ``output_paths``.
    """
    if isinstance(task, dict):
        task_key = str(task.get("task_key") or "")
        output_paths = tuple(str(p) for p in task.get("output_paths", ()) if p)
    else:
        task_key = str(getattr(task, "task_key", "") or "")
        output_paths = tuple(
            str(p) for p in getattr(task, "output_paths", ()) or () if p
        )

    if task_key in BOOTSTRAP_OUTPUT_CONTRACTS:
        return BOOTSTRAP_OUTPUT_CONTRACTS[task_key]

    return OutputContract(
        required_paths=output_paths,
        writable_paths=output_paths,
        readiness_paths=output_paths,
    )
