"""AutoNovel integration (Phase 5, Task 12).

Public surface:

- :mod:`.layout` — the artifact-layout bijection between a NovelKit novel
  workspace and an AutoNovel workspace (Task 12.2).
- :mod:`.adapter` — the seam that drives a generic AutoNovel chapter-writing
  loop with NovelKit's pipeline tool (Task 12.1), plus a concrete in-memory
  reference loop.
"""

from __future__ import annotations

from .adapter import (
    AutoNovelAdapter,
    AutoNovelLoop,
    AutoNovelWorkspace,
    InMemoryAutoNovelLoop,
    LoopStage,
    LoopStep,
    RunReport,
    StepResult,
    stage_for_task,
)
from .layout import (
    CANONICAL_NOVELKIT_ARTIFACTS,
    LAYOUT,
    ArtifactLayoutMap,
    to_autonovel,
    to_novelkit,
)

__all__ = [
    "AutoNovelAdapter",
    "AutoNovelLoop",
    "AutoNovelWorkspace",
    "InMemoryAutoNovelLoop",
    "LoopStage",
    "LoopStep",
    "RunReport",
    "StepResult",
    "stage_for_task",
    "ArtifactLayoutMap",
    "LAYOUT",
    "to_autonovel",
    "to_novelkit",
    "CANONICAL_NOVELKIT_ARTIFACTS",
]
