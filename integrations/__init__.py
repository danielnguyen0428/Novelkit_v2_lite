"""External-framework integration seams for NovelKit on Hermes.

Currently hosts the **AutoNovel** integration (Phase 5, Task 12): the adapter
that splices NovelKit's pipeline tool into a generic AutoNovel-style
chapter-writing loop, plus the artifact-layout mapping between a NovelKit novel
workspace and an AutoNovel workspace.
"""

from __future__ import annotations
