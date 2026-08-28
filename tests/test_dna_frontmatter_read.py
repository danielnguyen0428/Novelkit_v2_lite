"""Reading a single field out of PROJECT_DNA.md must not invent values.

``_dna_field`` backs the fallback path of ``_world_facts_block``,
``_dna_tail_reminder`` and ``_modern_register_allowed``: whenever
``PROJECT_DNA.fields.json`` lacks a key, the value comes from a regex over the
prose DNA. Two properties of that regex were wrong, and both were measured
against the 503 real ``PROJECT_DNA.md`` files in storage:

* ``\\s*`` after the key also matches a NEWLINE, so a key declared EMPTY in the
  frontmatter (``style_model:`` with nothing after it) silently absorbed the NEXT
  line's text. 476 of 503 files hit this; it put ``chính='STYLE_BLEND:'`` — not
  an author code at all — into the prose prompt of 200+ novels.
* The search ran over the whole capped read, not just the frontmatter, so the
  template's trailing ``## XIV. HYBRID GENRE EXAMPLES`` YAML comment block was
  indistinguishable from real metadata (39 real files carry it inside the read).

The third test covers the read-cap warning that made this visible in the Render
log: it fired on a file that was exactly at the cap (nothing truncated) and had
no dedup, producing 78 identical lines for one novel in one hour.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from integrations.autonovel.adapter import AutoNovelWorkspace
from integrations.autonovel.llm_loop import _DNA_MAX_CHARS, LLMAutoNovelLoop


def _workspace() -> AutoNovelWorkspace:
    root = Path(tempfile.mkdtemp()) / "dna-read"
    root.mkdir(parents=True)
    return AutoNovelWorkspace(root=root)


class _FakeClient:
    """Never called: these tests only exercise DNA reading."""

    config = None

    def complete(self, **_kw):  # noqa: ANN003
        raise AssertionError("no LLM call expected")


#: Verbatim shape of a real generated frontmatter: several keys are present but
#: EMPTY, which is what triggers the newline bug.
_REAL_FRONTMATTER = """---
generated: 2026-07-04
genre: xianxia
genre_primary: xianxia
genre_secondary:
hybrid_ratio:
style_model: NC
style_blend:
worldbuilding_guide: NC
cultivation_speed: Nội dung cultivation_speed
cultivation_age_benchmarks: []
output_language: vi
---

# PROJECT_DNA.md — demo

## XIV. HYBRID GENRE EXAMPLES

```yaml
# Example: Tiên Hiệp + Hắc Ám
# genre: hybrid
# genre_secondary: dark theme
# hybrid_ratio: 70-30
```
"""


def _loop_with(dna: str) -> tuple[LLMAutoNovelLoop, AutoNovelWorkspace]:
    ws = _workspace()
    ws.write("PROJECT_DNA.md", dna)
    return LLMAutoNovelLoop(client=_FakeClient()), ws


def test_empty_field_reads_empty_not_the_next_line():
    """``style_model:`` followed by ``style_blend:`` must not yield the latter."""
    loop, ws = _loop_with(_REAL_FRONTMATTER)

    # Present-and-empty keys must read as empty…
    assert loop._dna_field(ws, "genre_secondary") == ""
    assert loop._dna_field(ws, "hybrid_ratio") == ""
    assert loop._dna_field(ws, "style_blend") == ""
    # …while real values still read correctly.
    assert loop._dna_field(ws, "style_model") == "NC"
    assert loop._dna_field(ws, "genre_primary") == "xianxia"
    assert loop._dna_field(ws, "cultivation_speed") == "Nội dung cultivation_speed"


def test_empty_style_model_does_not_leak_a_fake_author_code():
    """The exact production symptom: a garbage code reaching the prose prompt."""
    loop, ws = _loop_with(
        _REAL_FRONTMATTER.replace("style_model: NC", "style_model:")
    )

    style = loop._dna_field(ws, "style_model")
    assert style == "", f"read a bogus author code: {style!r}"
    assert "STYLE_BLEND" not in style.upper()


def test_example_block_is_not_read_as_metadata():
    """A YAML EXAMPLE block after the frontmatter is documentation, not data."""
    loop, ws = _loop_with(_REAL_FRONTMATTER)

    # Declared empty in the frontmatter; only the EXAMPLE block says otherwise.
    assert loop._dna_field(ws, "genre_secondary") == ""
    assert loop._dna_field(ws, "hybrid_ratio") == ""
    # And `genre` must come from the frontmatter, not the example.
    assert loop._dna_field(ws, "genre") == "xianxia"


def test_field_outside_any_frontmatter_still_readable():
    """A hand-made DNA with no ``---`` block must not lose its fields.

    26 of the 503 real files have no frontmatter at all; refusing to read them
    would be a regression, so the anchored read falls back to the whole document.
    """
    loop, ws = _loop_with(
        "# PROJECT_DNA.md — handmade\n\nworld_era: cổ đại\nstyle_model: VN\n"
    )

    assert loop._dna_field(ws, "world_era") == "cổ đại"
    assert loop._dna_field(ws, "style_model") == "VN"


def test_cap_warning_not_emitted_when_nothing_is_truncated(caplog):
    """A DNA of exactly the cap length loses no text, so it must not warn."""
    body = "---\ngenre: xianxia\n---\n"
    exact = body + "x" * (_DNA_MAX_CHARS - len(body))
    assert len(exact) == _DNA_MAX_CHARS
    loop, ws = _loop_with(exact)

    with caplog.at_level(logging.WARNING):
        loop._dna(ws)

    assert not [r for r in caplog.records if "read cap" in r.message]


def test_cap_warning_is_emitted_once_per_workspace(caplog):
    """Warn on real truncation, but once — not on every prompt build."""
    loop, ws = _loop_with("---\ngenre: xianxia\n---\n" + "y" * (_DNA_MAX_CHARS + 500))

    with caplog.at_level(logging.WARNING):
        for _ in range(10):
            loop._dna(ws)

    hits = [r for r in caplog.records if "read cap" in r.message]
    assert len(hits) == 1, f"expected one warning, got {len(hits)}"
