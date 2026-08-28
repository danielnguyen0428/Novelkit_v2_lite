"""Guard tests for wiring the whole ``canon/system`` tree into the runtime.

These prove the fix for "Texture / Worldbuilding guide / Depth / Genre Operating
/ consistency / style canon never reached the model": every consumable file
under a genre pack must now be routed to at least one runtime channel — the
always-on persona block (:meth:`_genre_canon_block`) or the RAG index
(:meth:`_retrieve`). The coverage test walks the real ``canon/system`` tree so a
newly-added canon file that nobody wired in fails CI instead of silently rotting.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from integrations.autonovel.adapter import AutoNovelWorkspace, LoopStage, LoopStep
from integrations.autonovel.llm_loop import (
    _CANON_SYSTEM_ROOT,
    _CODE_NAME_ALIAS,
    _SYSTEM_CORE,
    _STORYDEPTH_FILE,
    _iter_system_canon,
    LLMAutoNovelLoop,
)
from webapp.api.dna_form import STYLE_BY_GENRE, canon_pack

# Files under a pack that are deliberately NOT fed to the LLM here: the language
# guard consumes vocabulary.txt, and .DS_Store is OS cruft.
_NON_LLM_NAMES = {"vocabulary.txt", ".DS_Store"}

# Every genre pack directory on disk (skip StoryDepth: it is the cross-genre
# field-execution file, asserted separately as an always-on persona law).
_PACK_DIRS = sorted(
    p
    for p in _CANON_SYSTEM_ROOT.iterdir()
    if p.is_dir() and p.name != "StoryDepth"
)

_AUTHOR_CASES = [
    (genre, option["value"])
    for genre, options in STYLE_BY_GENRE.items()
    for option in options
]


class _FakeClient:
    def complete(self, **_kwargs):  # noqa: ANN003
        return ""


class _CaptureClient:
    def __init__(self):
        self.calls: list[dict] = []

    def complete(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        return "Nội dung thử."


def _workspace() -> AutoNovelWorkspace:
    root = Path(tempfile.mkdtemp()) / "canon-wiring"
    root.mkdir(parents=True)
    return AutoNovelWorkspace(root=root)


def _consumable_files(pack_dir: Path) -> set[Path]:
    """Every file under a pack the LLM should see (excludes guard/OS files)."""
    return {
        p
        for p in pack_dir.rglob("*")
        if p.is_file() and p.name not in _NON_LLM_NAMES
    }


@pytest.mark.parametrize("pack_dir", _PACK_DIRS, ids=lambda p: p.name)
def test_every_pack_file_is_routed_to_a_runtime_channel(pack_dir: Path):
    """No consumable file in any genre pack is silently dropped.

    "Reachable" is computed as the union of the persona + rag channels over
    EVERY code present in the pick-one dirs (Author Style / Worldbuilding
    guide): a per-novel run only loads its own selected master, but every master
    file must be routable when its code is selected. That union must equal the
    full consumable file set — otherwise a canon file reaches no channel at all.
    """
    # A few WB-guide files predate the [CODE] naming (e.g. ThanDong ships as a
    # name-stem file reachable only via the alias code CD, which lives in Author
    # Style). So try every code found in EITHER pick-one dir as a candidate for
    # BOTH — the loader's alias fallback resolves the legacy names.
    all_codes = (
        set(_codes(pack_dir / "Author Style"))
        | set(_codes(pack_dir / "Worldbuilding guide"))
        # slug-named files (Sci-fi / Meta Genre / ThanDong) resolve only via
        # their alias code, so every alias key is a candidate too.
        | set(_CODE_NAME_ALIAS)
    ) or {""}
    reachable: set[Path] = set()
    for style_code in all_codes:
        for wb_code in all_codes:
            split = _iter_system_canon(
                pack_dir, style_code=style_code, wb_code=wb_code
            )
            reachable |= set(split["persona"]) | set(split["rag"])
    missing = _consumable_files(pack_dir) - reachable
    assert not missing, (
        f"{pack_dir.name}: {len(missing)} canon file(s) reach NO runtime "
        f"channel: {sorted(p.name for p in missing)}"
    )


@pytest.mark.parametrize("pack_dir", _PACK_DIRS, ids=lambda p: p.name)
def test_rag_channel_is_a_superset_of_persona(pack_dir: Path):
    """Every always-on persona file is also retrievable (persona ⊆ rag)."""
    style_code = _first_code(pack_dir / "Author Style")
    wb_code = _first_code(pack_dir / "Worldbuilding guide")
    split = _iter_system_canon(
        pack_dir, style_code=style_code, wb_code=wb_code
    )
    assert set(split["persona"]) <= set(split["rag"])


def test_storydepth_field_execution_file_exists():
    """The cross-genre StoryDepth canon (always-on persona law) is present."""
    assert _STORYDEPTH_FILE.is_file(), _STORYDEPTH_FILE


def test_pick_one_dirs_select_exactly_the_coded_file():
    """Author Style / Worldbuilding guide load ONLY the novel's chosen master."""
    xianxia = _CANON_SYSTEM_ROOT / "Xianxia"
    if not xianxia.is_dir():
        pytest.skip("Xianxia pack not present")
    split = _iter_system_canon(xianxia, style_code="NC", wb_code="NC")
    author_files = [p for p in split["persona"] if p.parent.name == "Author Style"]
    wb_files = [p for p in split["rag"] if p.parent.name == "Worldbuilding guide"]
    assert len(author_files) == 1 and "[NC]" in author_files[0].name
    assert len(wb_files) == 1 and "[NC]" in wb_files[0].name


def test_xianxia_depth_laws_are_wired_by_channel():
    """The Xianxia depth laws that used to be dead now reach the runtime.

    Cost-tuning split (prefix-cache + persona-cap): Texture stays always-on in
    the persona block (it drives prose feel, must apply every call), while the
    heavier lookup-oriented Progression + World laws move to RAG-only — still
    reachable via :meth:`_retrieve`, just not force-fed into every prompt.
    """
    xianxia = _CANON_SYSTEM_ROOT / "Xianxia"
    if not xianxia.is_dir():
        pytest.skip("Xianxia pack not present")
    split = _iter_system_canon(xianxia, style_code="NC", wb_code="NC")
    persona_names = {p.name for p in split["persona"]}
    rag_names = {p.name for p in split["rag"]}
    # Texture is always-on (persona) — and, like every persona file, also in RAG.
    assert "Tu_Tien_Texture_Floor.md" in persona_names
    # Progression + World are RAG-only: reachable but not in the persona block.
    assert "Cultivation_Progression_System.md" not in persona_names
    assert "Xianxia_World_Operating_System.md" not in persona_names
    assert "Cultivation_Progression_System.md" in rag_names
    assert "Xianxia_World_Operating_System.md" in rag_names


def test_genre_canon_block_includes_the_wired_canon():
    """End-to-end: the assembled persona block carries the genre canon text.

    Writes a minimal Xianxia DNA (canon_pack + style_model + worldbuilding_guide)
    and asserts the persona block contains markers from the Author Style, the
    Texture floor, and the StoryDepth field-execution file — i.e. the canon
    actually reaches the system prompt, not just the file list.
    """
    if not (_CANON_SYSTEM_ROOT / "Xianxia").is_dir():
        pytest.skip("Xianxia pack not present")
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: xianxia\n"
        "canon_pack: system/Xianxia\n"
        "style_model: NC\n"
        "worldbuilding_guide: NC\n"
        "---\n"
        "- **Tên tác phẩm:** Thí Nghiệm Canon\n",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    block = loop._genre_canon_block(ws)
    assert block, "persona canon block is empty"
    # Section headers name the source dir/file so we can assert real inclusion.
    assert "Author Style" in block
    assert "Texture" in block
    assert _STORYDEPTH_FILE.name in block


def test_vn_canon_block_contains_only_the_neutral_author_profile():
    """The selected VN file remains routed, without its former prose rules."""
    if not (_CANON_SYSTEM_ROOT / "Xianxia").is_dir():
        pytest.skip("Xianxia pack not present")
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: xianxia\n"
        "canon_pack: system/Xianxia\n"
        "style_model: VN\n"
        "worldbuilding_guide: VN\n"
        "---\n"
        "- **Tên tác phẩm:** Thí Nghiệm Văn Vực\n",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    block = loop._genre_canon_block(ws)
    assert "Mã tác giả: `VN`" in block
    assert "chỉ cung cấp thông tin nhận diện khái quát" in block
    assert "VĂN VỰC & NHỊP CÂU — SYSTEM GATE" not in block


@pytest.mark.parametrize(
    "style_code",
    [option["value"] for option in STYLE_BY_GENRE["xianxia"]],
)
def test_selected_xianxia_author_is_a_final_neutral_reference(style_code: str):
    """Every selected author ends with an explicit anti-imitation guard."""
    if not (_CANON_SYSTEM_ROOT / "Xianxia").is_dir():
        pytest.skip("Xianxia pack not present")
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: xianxia\n"
        "canon_pack: system/Xianxia\n"
        f"style_model: {style_code}\n"
        f"worldbuilding_guide: {style_code}\n"
        "---\n",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    block = loop._persona(
        LoopStep(
            task_key="chapter.0001.write",
            stage=LoopStage.DRAFT,
            phase="draft",
            command="write",
            agent_role="Prose Writer",
            chapter=1,
            arc=1,
            input_paths=(),
            output_paths=(),
            context_query=None,
        ),
        ws,
    )

    reference = block.index("## AUTHOR REFERENCE — CHỈ NHẬN DIỆN")
    selected_path = next(
        path
        for path in loop._system_canon(ws)["persona"]
        if path.parent.name == "Author Style"
        and path.name.endswith("_xianxia_rules.md")
    )
    selected_reference = block.index(
        f"### AUTHOR REFERENCE / {selected_path.name}"
    )
    generic_style = block.index("### Xianxia / Xianxia_style.md")
    soul = block.index("HỒ SƠ CHUYÊN GIA (SOUL):")
    assert generic_style < soul < reference < selected_reference
    tail = block[reference:]
    assert "không suy luận, tái tạo hoặc mô phỏng" in tail.lower()
    assert f"Mã tác giả: `{style_code}`" in tail
    assert "## STYLE AUTHORITY — BẮT BUỘC" not in tail


def test_hybrid_uses_the_secondary_packs_selected_author():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: hybrid\n"
        "genre_primary: xianxia\n"
        "genre_secondary: romance\n"
        "canon_pack: system/Xianxia\n"
        "canon_pack_secondary: system/Romance\n"
        "style_model: VN\n"
        "style_blend: CM\n"
        "worldbuilding_guide: VN\n"
        "---\n",
    )
    persona = LLMAutoNovelLoop(client=_FakeClient())._system_canon(ws)["persona"]
    author_files = [p for p in persona if p.parent.name == "Author Style"]
    assert len(author_files) == 2
    assert any("[VN]" in p.name for p in author_files)
    assert any("[CM]" in p.name for p in author_files)


def test_same_genre_style_blend_loads_both_selected_authors():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: hybrid\n"
        "genre_primary: xianxia\n"
        "genre_secondary: xianxia\n"
        "canon_pack: system/Xianxia\n"
        "canon_pack_secondary: system/Xianxia\n"
        "style_model: VN\n"
        "style_blend: NC\n"
        "worldbuilding_guide: VN\n"
        "---\n",
    )
    persona = LLMAutoNovelLoop(client=_FakeClient())._system_canon(ws)["persona"]
    author_files = [p for p in persona if p.parent.name == "Author Style"]
    assert len(author_files) == 2
    assert any("[VN]" in p.name for p in author_files)
    assert any("[NC]" in p.name for p in author_files)


def test_worldbuilding_excerpt_falls_back_to_selected_author_style():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: xianxia\n"
        "canon_pack: system/Xianxia\n"
        "style_model: OT\n"
        "worldbuilding_guide: OT\n"
        "---\n",
    )
    excerpt = LLMAutoNovelLoop(client=_FakeClient())._wb_guide_excerpt(ws)
    assert "NGUỒN THAM CHIẾU: Author Style/" in excerpt
    assert "PROJECT_DNA và database của truyện luôn thắng" in excerpt


@pytest.mark.parametrize("genre,style_code", _AUTHOR_CASES)
def test_every_configured_author_routes_voice_and_worldbuilding(
    genre: str, style_code: str
):
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        f"genre: {genre}\n"
        f"genre_primary: {genre}\n"
        f"canon_pack: system/{canon_pack(genre)}\n"
        f"style_model: {style_code}\n"
        f"worldbuilding_guide: {style_code}\n"
        "---\n",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    author_files = [
        p for p in loop._system_canon(ws)["persona"]
        if p.parent.name == "Author Style"
    ]
    assert len(author_files) == 1, (genre, style_code, author_files)
    assert loop._wb_guide_excerpt(ws).strip(), (genre, style_code)


def test_system_core_treats_author_profiles_as_identifiers_only():
    assert "Author Style đã chọn chỉ là metadata nhận diện" in _SYSTEM_CORE
    assert "không suy luận, tái tạo hoặc mô phỏng văn phong" in _SYSTEM_CORE
    assert "Worldbuilding guide đã chọn quyết định" in _SYSTEM_CORE
    assert "Author Style đã chọn quyết định giọng văn" not in _SYSTEM_CORE


def test_draft_prompt_keeps_author_code_as_neutral_metadata():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: xianxia\n"
        "genre_primary: xianxia\n"
        "canon_pack: system/Xianxia\n"
        "style_model: VN\n"
        "worldbuilding_guide: VN\n"
        "target_words_per_chapter: 500\n"
        "output_language: vi\n"
        "---\n",
    )
    ws.write("outlines/chapter_0001.md", "Một cảnh thử.")
    client = _CaptureClient()
    step = LoopStep(
        task_key="chapter.0001.write",
        stage=LoopStage.DRAFT,
        phase="draft",
        command="WRITE_PROSE",
        agent_role="prose_writer",
        chapter=1,
        arc=1,
        input_paths=("outlines/chapter_0001.md",),
        output_paths=("drafts/chapter_0001.md",),
        context_query=None,
    )
    LLMAutoNovelLoop(client=client).draft(step, ws)
    prompt = client.calls[0]["user"]
    assert "THAM CHIẾU TÁC GIẢ: chính=VN" in prompt
    assert "không suy luận hoặc mô phỏng văn phong" in prompt
    assert "Thi hành đúng Author Style đã chọn" not in prompt


def test_revision_prompt_keeps_project_voice_without_author_imitation():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: xianxia\n"
        "genre_primary: xianxia\n"
        "canon_pack: system/Xianxia\n"
        "style_model: VN\n"
        "worldbuilding_guide: VN\n"
        "target_words_per_chapter: 500\n"
        "output_language: vi\n"
        "---\n",
    )
    client = _CaptureClient()
    step = LoopStep(
        task_key="chapter.0001.review",
        stage=LoopStage.CRITIQUE,
        phase="review",
        command="REVIEW_PROSE",
        agent_role="reviewer",
        chapter=1,
        arc=1,
        input_paths=(),
        output_paths=(),
        context_query=None,
    )
    LLMAutoNovelLoop(client=client)._revise_chapter(
        step, ws, 1, "Bản cũ.", "Sửa nhịp câu."
    )
    prompt = client.calls[0]["user"]
    assert "giữ giọng dự án theo PROJECT_DNA" in prompt
    assert "không mô phỏng văn phong của tác giả có tên" in prompt
    assert "thẩm quyền giọng văn" not in prompt


def test_reviewer_caps_a_chapter_that_misses_the_project_voice_contract():
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: xianxia\n"
        "genre_primary: xianxia\n"
        "canon_pack: system/Xianxia\n"
        "style_model: VN\n"
        "worldbuilding_guide: VN\n"
        "output_language: vi\n"
        "---\n",
    )
    client = _CaptureClient()
    step = LoopStep(
        task_key="chapter.0001.review",
        stage=LoopStage.CRITIQUE,
        phase="review",
        command="REVIEW_PROSE",
        agent_role="reviewer",
        chapter=1,
        arc=1,
        input_paths=(),
        output_paths=(),
        context_query=None,
    )
    LLMAutoNovelLoop(client=client)._critique_once(step, ws, "Bản chương.")
    prompt = client.calls[0]["user"]
    assert "giọng dự án không bám PROJECT_DNA" in prompt
    assert "Không đánh giá bằng mức độ giống một tác giả có tên" in prompt
    assert "tổng điểm không được quá 69/100" in prompt
    assert "worldbuilding mâu thuẫn" in prompt


def test_project_voice_or_worldbuilding_failure_caps_review_deterministically():
    score, verdict = LLMAutoNovelLoop._apply_author_contract_penalty(
        "## Project Voice Gate: FAIL\n## Worldbuilding Gate: PASS\n"
        "## Verdict: PASS\n**Điểm:** 92/100",
        92.0,
        "pass",
    )
    assert score == 69.0
    assert verdict == "hard_fail"


def _codes(dir_path: Path) -> list[str]:
    """Every ``[CODE]`` present in a pick-one dir (Author Style / WB guide)."""
    if not dir_path.is_dir():
        return []
    codes: list[str] = []
    for p in sorted(dir_path.glob("[[]*[]]*.md")):
        name = p.name
        if name.startswith("[") and "]" in name:
            codes.append(name[1 : name.index("]")])
    return codes


def _first_code(dir_path: Path) -> str:
    """Return the ``[CODE]`` of the first coded file in a pick-one dir (or "")."""
    codes = _codes(dir_path)
    return codes[0] if codes else ""


@pytest.mark.parametrize(
    "style_code",
    ["NC", "VN", "PL", "TH"],
)
def test_tail_register_ignores_author_specific_lexical_rules(style_code: str):
    """Every author code receives the same genre-level register contract."""
    if not (_CANON_SYSTEM_ROOT / "Xianxia").is_dir():
        pytest.skip("Xianxia pack not present")
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        "genre: xianxia\n"
        "canon_pack: system/Xianxia\n"
        f"style_model: {style_code}\n"
        f"worldbuilding_guide: {style_code}\n"
        "---\n",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    tail = loop._dna_tail_reminder(ws)
    assert "REGISTER XIANXIA" in tail
    assert "cấm tiếng lóng hiện đại" in tail
    assert "NGOẠI LỆ lexical" not in tail
    assert "Xưng hô" in tail


@pytest.mark.parametrize(
    "genre,style_code",
    [
        ("romance", "CM"),
        ("urban", "KV"),
        ("scifi", "LTH"),
        ("time_travel", "MN"),
        ("meta_genre", "MV"),
    ],
)
def test_neutral_author_reference_guard_applies_to_every_genre(
    genre: str, style_code: str
):
    """Named-author profiles stay informational across every supported genre."""
    pack = canon_pack(genre)
    if not (_CANON_SYSTEM_ROOT / pack).is_dir():
        pytest.skip(f"{pack} pack not present")
    ws = _workspace()
    ws.write(
        "PROJECT_DNA.md",
        "---\n"
        f"genre: {genre}\n"
        f"canon_pack: system/{pack}\n"
        f"style_model: {style_code}\n"
        "---\n",
    )
    loop = LLMAutoNovelLoop(client=_FakeClient())
    selected = [
        p for p in loop._system_canon(ws)["persona"]
        if p.parent.name == "Author Style"
    ]
    assert selected, f"no Author Style resolved for {genre}/{style_code}"

    block = loop._selected_author_style_block(ws)
    assert "## AUTHOR REFERENCE — CHỈ NHẬN DIỆN" in block
    assert "không suy luận, tái tạo hoặc mô phỏng" in block.lower()
    for path in selected:
        assert f"### AUTHOR REFERENCE / {path.name}" in block
        assert path.read_text(encoding="utf-8").strip() in block
    assert "## STYLE AUTHORITY — BẮT BUỘC" not in block
