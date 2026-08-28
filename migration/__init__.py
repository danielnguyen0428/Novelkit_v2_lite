"""Migration tooling for the NovelKit -> Hermes/AutoNovel transition.

Phase 0 lives here: the inventory scanner that classifies every file under
``_novelkit_source/`` and the frozen must-keep baseline used to prove 100%
creative-asset coverage (Requirement 1, Property 10).
"""

from .inventory import (
    Category,
    FileRecord,
    MappingStatus,
    build_inventory,
    classify,
    scan,
)

__all__ = [
    "Category",
    "MappingStatus",
    "FileRecord",
    "classify",
    "scan",
    "build_inventory",
]
