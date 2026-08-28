"""Byte-level proof that the selected config/canon reaches the model.

The pre-existing wiring tests assert *file lists* (every canon file is routed to
some channel) and *marker strings* (the persona block contains "Author Style").
Both passed while the runtime still sent the model zero bytes of the selected
Worldbuilding guide, zero bytes of the consistency rules, and none of the
``world_*`` / ``system_*`` DNA fields — the retrieval budget was consumed by a
single unsplit chunk and the DNA digest dropped 67 of 82 fields.

These tests assert on the ACTUAL prompt string handed to the client, using text
sampled from the canon files on disk. A regression that silently stops feeding a
selected asset fails here instead of shipping.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest

from integrations.autonovel.adapter import AutoNovelWorkspace, LoopStage, LoopStep
from integrations.autonovel.llm_loop import _CANON_SYSTEM_ROOT, LLMAutoNovelLoop

_XIANXIA = _CANON_SYSTEM_ROOT / "Xianxia"

pytestmark = pytest.mark.skipif(
    not _XIANXIA.is_dir(), reason="Xianxia canon pack not present"
)


class _CaptureClient:
    """Records every ``complete()`` call so tests can inspect the real prompt."""

    def __init__(self, reply: str = "Nội dung thử."):
        self.calls: list[dict] = []
        self._reply = reply

    def complete(self, **kwargs):  # noqa: ANN003
        self.calls.append(kwargs)
        return self._reply


_FIELDS = {
    "title": "Thí Nghiệm Canon",
    "logline": "Một kẻ mang thân phận Tà Đế phải sống lại kịch bản đã định.",
    "genre": "xianxia",
    "genre_primary": "xianxia",
    "theme": "Định mệnh và ý chí",
    "tone": "trầm, nhiều tính toán",
    "style_execution": "câu vừa làm trục, hài khô sinh từ tình huống",
    "mc_want": "phá vỡ kịch bản gốc",
    "mc_need": "chấp nhận bản ngã",
    "world_name": "Vạn Cổ Đại Lục",
    "world_era": "Hậu Thượng Cổ, các chủng tộc tranh giành khí vận",
    "world_secret": "Đại Lục là tác phẩm bị bỏ rơi của một Tạo Vật Chủ thất bại.",
    "world_locations": "Tà Cung trên đỉnh núi Lạc Hồn; Thanh Vân Tông ở Đông Vực",
    "world_mindset": "Quy luật Ngòi Bút Định Mệnh chi phối mọi kết cục.",
    "system_name": "Thiên Địa Tu Hành Cảnh Giới",
    "system_tiers": "Luyện Khí, Trúc Cơ, Kim Đan, Nguyên Anh, Hóa Thần, Đại Thừa",
    "system_cost": "Can thiệp số mệnh thì hao tổn thọ nguyên.",
    "system_golden_finger": "Tà Đạo Bút Ký, bản thảo gốc hóa pháp bảo.",
    "system_bottleneck": "Thiên mệnh xiềng xích sinh biến số mới mỗi lần phá kịch bản.",
    "cultivation_speed": "slow",
    "cultivation_age_benchmarks": "Trúc Cơ 26, Kim Đan 30, Nguyên Anh 40",
    "mc_name": "Tà Đế",
    "antagonist_name": "Diệp Vân",
    "target_words_per_chapter": "2000",
}

_FRONTMATTER = (
    "---\n"
    "genre: xianxia\n"
    "genre_primary: xianxia\n"
    "canon_pack: system/Xianxia\n"
    "style_model: NC\n"
    "worldbuilding_guide: NC\n"
    "target_words_per_chapter: 2000\n"
    "---\n"
    "# PROJECT_DNA.md — Thí Nghiệm Canon\n"
)


def _workspace(*, style: str = "NC", wb: str = "NC", genre: str = "xianxia",
               pack: str = "system/Xianxia") -> AutoNovelWorkspace:
    root = Path(tempfile.mkdtemp()) / "canon-bytes"
    root.mkdir(parents=True)
    ws = AutoNovelWorkspace(root=root)
    front = (
        "---\n"
        f"genre: {genre}\n"
        f"genre_primary: {genre}\n"
        f"canon_pack: {pack}\n"
        f"style_model: {style}\n"
        f"worldbuilding_guide: {wb}\n"
        "target_words_per_chapter: 2000\n"
        "---\n"
        "# PROJECT_DNA.md — Thí Nghiệm Canon\n"
    )
    ws.write("PROJECT_DNA.md", front)
    fields = dict(_FIELDS)
    fields["genre"] = genre
    fields["genre_primary"] = genre
    fields["style_model"] = style
    fields["worldbuilding_guide"] = wb
    ws.write("PROJECT_DNA.fields.json", json.dumps(fields, ensure_ascii=False))
    ws.write(
        "outlines/chapter_0001.md",
        "# Chương 1\n- Beat 1: Tà Đế tỉnh lại trong Tà Cung.\n"
        "- Beat 2: phát hiện tu vi rơi về Luyện Khí.\n",
    )
    return ws


def _draft_step() -> LoopStep:
    return LoopStep(
        task_key="chapter.0001.write",
        stage=LoopStage.DRAFT,
        phase="draft",
        command="WRITE_CHAPTER",
        agent_role="Prose Writer",
        chapter=1,
        arc=1,
        input_paths=("outlines/chapter_0001.md",),
        output_paths=("drafts/chapter_0001.md",),
        context_query=None,
    )


def _draft_prompt(ws: AutoNovelWorkspace) -> dict:
    client = _CaptureClient()
    LLMAutoNovelLoop(client=client).draft(_draft_step(), ws)
    assert client.calls, "draft() never called the client"
    call = client.calls[0]
    return {
        "user": call.get("user") or "",
        "system": call.get("system") or "",
        "all": f"{call.get('system') or ''}\n{call.get('user') or ''}",
    }


# --------------------------------------------------------------------------- #
# World / system facts from the DNA sidecar
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "field",
    [
        "world_name",
        "world_era",
        "world_secret",
        "world_locations",
        "system_name",
        "system_tiers",
        "system_cost",
        "system_golden_finger",
        "system_bottleneck",
        "cultivation_age_benchmarks",
    ],
)
def test_world_and_system_facts_reach_the_draft_prompt(field: str):
    """Every configured world/system fact is IN the prompt, not just referenced.

    The digest used to carry 15 of 82 fields, so a novel could declare its
    cultivation ladder and world secret and the writer model would never see
    either — it invented its own and the prose contradicted the DNA.
    """
    prompt = _draft_prompt(_workspace())
    value = _FIELDS[field]
    # Compare on a distinctive fragment: long values may be per-field capped.
    fragment = value[:40]
    assert fragment in prompt["all"], (
        f"{field} missing from the draft prompt (looked for {fragment!r})"
    )


def test_world_facts_block_is_labelled_as_immutable():
    prompt = _draft_prompt(_workspace())
    assert "SỰ THẬT THẾ GIỚI" in prompt["user"]


# --------------------------------------------------------------------------- #
# The selected Worldbuilding guide
# --------------------------------------------------------------------------- #


def _guide_path(code: str = "NC") -> Path:
    matches = sorted((_XIANXIA / "Worldbuilding guide").glob(f"[[]{code}[]]*.md"))
    assert matches, f"no worldbuilding guide for code {code}"
    return matches[0]


def _distinctive_lines(path: Path, *, count: int = 40, min_len: int = 45) -> list[str]:
    """Content lines long enough to be unique to this file."""
    out: list[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip().lstrip("#-*> ").strip()
        if len(line) >= min_len and not line.startswith("|"):
            out.append(line)
        if len(out) >= count:
            break
    return out


def test_selected_worldbuilding_guide_contributes_real_text():
    """The chosen guide's own prose appears in the draft prompt.

    ``_wb_guide_excerpt`` existed but was only called from ``worldbuild()``, so
    a chapter draft was told to "follow the selected Worldbuilding guide" with
    zero bytes of that guide attached.
    """
    prompt = _draft_prompt(_workspace())
    lines = _distinctive_lines(_guide_path("NC"))
    assert lines, "guide yielded no comparable lines"
    hits = [line for line in lines if line[:45] in prompt["all"]]
    assert hits, (
        "no line from the selected Worldbuilding guide reached the prompt; "
        f"checked {len(lines)} candidate lines"
    )


def test_unselected_worldbuilding_guide_is_not_leaked():
    """Choosing NC must not pull another master's guide into the prompt."""
    prompt = _draft_prompt(_workspace(style="NC", wb="NC"))
    other = _guide_path("VN")
    lines = _distinctive_lines(other, count=25, min_len=60)
    leaked = [line for line in lines if line[:60] in prompt["all"]]
    assert not leaked, f"unselected guide text leaked: {leaked[:2]}"


# --------------------------------------------------------------------------- #
# Retrieval actually surfaces multiple canon sources
# --------------------------------------------------------------------------- #


def test_retrieval_surfaces_several_distinct_canon_sources():
    """A retrieval pass must return more than one source.

    Before the splitter, one unsplit file consumed the whole budget: every
    query returned exactly one chunk, and the caller's hard truncation left only
    that file's first 3000 chars.
    """
    ws = _workspace()
    loop = LLMAutoNovelLoop(client=_CaptureClient())
    canon, _novel = loop._retrieve_split(
        ws,
        "cảnh giới tu luyện đột phá tông môn thế giới",
        canon_chars=7000,
        novel_chars=4000,
        chapter=1,
    )
    sources = set(re.findall(r"<!-- source: ([^|]+)\|", canon))
    assert len(sources) >= 2, f"retrieval collapsed to {sources}"


def test_canon_chunks_are_bounded():
    """No single chunk may monopolise the retrieval budget."""
    ws = _workspace()
    loop = LLMAutoNovelLoop(client=_CaptureClient())
    chunks = loop._canon_chunks(ws)
    assert chunks, "no canon chunks produced"
    oversized = [c for c in chunks if len(c.content) > 3000]
    assert not oversized, (
        f"{len(oversized)} chunk(s) exceed 3000 chars; largest="
        f"{max(len(c.content) for c in oversized)}"
    )


def test_consistency_rules_are_retrievable_by_their_own_headings():
    """The 74K-char consistency rules must be reachable, not just indexed."""
    ws = _workspace()
    loop = LLMAutoNovelLoop(client=_CaptureClient())
    rules = _XIANXIA / "Xianxia_consistency_rules.md"
    headings = [
        m.group(2).strip()
        for m in re.finditer(r"^(#{2,3})\s+(.+)$", rules.read_text(encoding="utf-8"),
                            re.MULTILINE)
        if len(m.group(2).strip()) > 12
    ][:12]
    assert headings, "no usable headings in the consistency rules"
    reached = False
    for heading in headings:
        block = loop._retrieve_chunks(
            loop._canon_chunks(ws), heading, max_chars=6000, chapter=1
        )
        if "Xianxia_consistency_rules" in block:
            reached = True
            break
    assert reached, (
        "consistency rules never surfaced for any of their own headings"
    )


# --------------------------------------------------------------------------- #
# Author reference selection is honoured, without prose imitation rules
# --------------------------------------------------------------------------- #


def _style_path(code: str) -> Path:
    matches = sorted((_XIANXIA / "Author Style").glob(f"[[]{code}[]]*.md"))
    assert matches, f"no author style for {code}"
    return matches[0]


@pytest.mark.parametrize("code", ["NC", "VN", "TD"])
def test_selected_author_reference_reaches_the_system_prompt(code: str):
    prompt = _draft_prompt(_workspace(style=code, wb=code))
    lines = _distinctive_lines(_style_path(code), count=30, min_len=45)
    assert lines, f"style {code} yielded no comparable lines"
    hits = [line for line in lines if line[:45] in prompt["system"]]
    assert hits, f"selected author reference {code} contributed no text"
    assert "AUTHOR REFERENCE — CHỈ NHẬN DIỆN" in prompt["system"]


def test_switching_author_reference_changes_only_the_selected_metadata():
    """NC and VN must route their own neutral reference file.

    The leak check only considers VN lines that are absent from the NC profile
    on disk: every author profile shares a boilerplate preamble (precedence
    notes, canon entry point), so a shared sentence appearing in an NC prompt is
    correct, not a leak. Only VN-exclusive text is evidence of misrouting.
    """
    nc = _draft_prompt(_workspace(style="NC", wb="NC"))["system"]
    vn = _draft_prompt(_workspace(style="VN", wb="VN"))["system"]
    assert nc != vn, "author selection had no effect on the system prompt"
    nc_text = _style_path("NC").read_text(encoding="utf-8")
    vn_lines = [
        line
        for line in _distinctive_lines(_style_path("VN"), count=60, min_len=60)
        if line[:60] not in nc_text
    ]
    assert vn_lines, "VN profile yielded no VN-exclusive lines to compare"
    leaked = [line for line in vn_lines if line[:60] in nc]
    assert not leaked, f"VN-only style text present in an NC novel: {leaked[:2]}"


# --------------------------------------------------------------------------- #
# Cross-genre isolation
# --------------------------------------------------------------------------- #


def test_a_scifi_novel_gets_no_xianxia_canon():
    """A non-xianxia novel must not silently inherit the xianxia pack.

    Eleven independent ``_g(fields, "genre", "xianxia")`` fallbacks meant a novel
    with a missing/other genre could be processed as xianxia with no error.
    """
    pack = _CANON_SYSTEM_ROOT / "Sci-fi"
    if not pack.is_dir():
        pytest.skip("Sci-fi pack not present")
    ws = _workspace(genre="scifi", pack="system/Sci-fi", style="", wb="")
    prompt = _draft_prompt(ws)
    xianxia_lines = _distinctive_lines(
        _XIANXIA / "Xianxia_style.md", count=25, min_len=60
    )
    leaked = [line for line in xianxia_lines if line[:60] in prompt["all"]]
    assert not leaked, f"xianxia canon leaked into a scifi novel: {leaked[:2]}"


# --------------------------------------------------------------------------- #
# The reviewer must judge against the SAME facts the writer was given
# --------------------------------------------------------------------------- #


def _review_step() -> LoopStep:
    return LoopStep(
        task_key="chapter.0001.review",
        stage=LoopStage.CRITIQUE,
        phase="review",
        command="REVIEW_CHAPTER",
        agent_role="Quality Auditor",
        chapter=1,
        arc=1,
        input_paths=(),
        output_paths=(),
        context_query=None,
    )


@pytest.mark.parametrize("fact", ["system_tiers", "world_name"])
def test_critique_prompt_carries_the_world_facts_it_gates_on(fact: str):
    """The critique enforces a "Worldbuilding Gate" — it must see the facts.

    Scoring a chapter for world consistency while the prompt never states the
    realm ladder or the world's name makes the gate a coin flip: the reviewer
    could only fail prose it had no contract for.
    """
    ws = _workspace()
    client = _CaptureClient()
    LLMAutoNovelLoop(client=client)._critique_once(
        _review_step(), ws, "Chương thử nghiệm."
    )
    prompt = client.calls[0]["user"]
    value = json.loads(
        (ws.root / "PROJECT_DNA.fields.json").read_text(encoding="utf-8")
    )[fact]
    assert value[:40] in prompt, f"{fact} missing from the critique prompt"


def test_revision_prompt_carries_the_world_facts():
    """A rewrite must not be free to invent a new realm ladder."""
    ws = _workspace()
    client = _CaptureClient()
    LLMAutoNovelLoop(client=client)._revise_chapter(
        _review_step(), ws, 1, "Bản cũ.", "Sửa nhịp câu."
    )
    prompt = client.calls[0]["user"]
    tiers = json.loads(
        (ws.root / "PROJECT_DNA.fields.json").read_text(encoding="utf-8")
    )["system_tiers"]
    assert tiers[:40] in prompt, "revision prompt lost the realm ladder"


# --------------------------------------------------------------------------- #
# Register contract comes from config, not from `if genre == "..."` in code
# --------------------------------------------------------------------------- #


def test_register_rules_are_config_driven_not_hardcoded():
    """Removing the rules from config must remove them from the prompt.

    The xianxia register used to live as literal Vietnamese strings inside two
    `if genre == "xianxia"` branches (one in llm_loop, one in dna_form) that had
    already drifted apart. If this test can flip the prompt by editing only the
    JSON, the branch is genuinely gone.
    """
    from tools.novelkit_language_guard_tool import load_profile

    profile = load_profile("xianxia")
    assert profile.register_rules, (
        "xianxia guard profile carries no register_rules — the contract is "
        "still hardcoded somewhere"
    )
    marker = profile.register_rules[0][:40]
    prompt = _draft_prompt(_workspace(style="NC", wb="NC"))["user"]
    assert marker in prompt, "config register rule never reached the prompt"


def test_author_specific_register_overrides_are_not_applied():
    """Legacy named-author overrides must not affect generated prose prompts."""
    from tools.novelkit_language_guard_tool import load_profile

    profile = load_profile("xianxia")
    vn_only = profile.style_overrides.get("VN")
    if not vn_only:
        pytest.skip("no VN style override configured")
    marker = vn_only[0][:40]
    vn_prompt = _draft_prompt(_workspace(style="VN", wb="VN"))["user"]
    nc_prompt = _draft_prompt(_workspace(style="NC", wb="NC"))["user"]
    assert marker not in vn_prompt
    assert marker not in nc_prompt


def test_a_genre_without_register_rules_gets_none():
    """Genres with no configured rules must not inherit the xianxia contract."""
    from tools.novelkit_language_guard_tool import load_profile

    xianxia_marker = load_profile("xianxia").register_rules[0][:40]
    romance = load_profile("romance")
    if romance.register_rules:
        pytest.skip("romance now configures its own register rules")
    pack = _CANON_SYSTEM_ROOT / "Romance"
    if not pack.is_dir():
        pytest.skip("Romance pack not present")
    prompt = _draft_prompt(
        _workspace(genre="romance", pack="system/Romance", style="CM", wb="CM")
    )["user"]
    assert xianxia_marker not in prompt, (
        "xianxia register contract applied to a romance novel"
    )


# --------------------------------------------------------------------------- #
# Outline stage — the beats the draft is then ordered to follow
# --------------------------------------------------------------------------- #


def _outline_prompt(ws: AutoNovelWorkspace) -> dict:
    client = _CaptureClient("# Chương 1\n- Beat: thử.")
    step = LoopStep(
        task_key="chapter.0001.outline",
        stage=LoopStage.OUTLINE,
        phase="outline",
        command="WRITE_OUTLINE",
        agent_role="Plot Weaver",
        chapter=1,
        arc=1,
        input_paths=(),
        output_paths=("outlines/chapter_0001.md",),
        context_query=None,
    )
    LLMAutoNovelLoop(client=client).outline(step, ws)
    assert client.calls, "outline() never called the client"
    call = client.calls[0]
    return {
        "user": call.get("user") or "",
        "system": call.get("system") or "",
    }


@pytest.mark.parametrize(
    "field", ["world_name", "system_tiers", "system_golden_finger", "world_secret"]
)
def test_outline_prompt_carries_the_world_facts(field: str):
    """The outline picks realms and factions, so it must know the settled ones.

    Grounding only the draft is not enough: ``draft`` is instructed to follow the
    outline, so an outline that invented a realm ladder made the prose wrong even
    with perfect draft grounding. The fabrication has to be blocked one stage
    earlier, where it actually enters the pipeline.
    """
    prompt = _outline_prompt(_workspace())["user"]
    value = str(_FIELDS[field])
    probe = value[:40] if len(value) > 40 else value
    assert probe in prompt, f"{field} missing from the outline prompt"


def test_outline_prompt_separates_canon_and_novel_ground():
    """Outline retrieval must not let the dense novel artifacts starve canon."""
    prompt = _outline_prompt(_workspace())["user"]
    assert "CANON THỂ LOẠI TRA CỨU" in prompt, (
        "outline has no dedicated genre-canon retrieval block"
    )


def test_outline_prompt_surfaces_more_than_one_source():
    """A single unsplit chunk must not consume the whole outline budget."""
    prompt = _outline_prompt(_workspace())["user"]
    sources = set(re.findall(r"<!-- source: ([^|]+)\|", prompt))
    assert len(sources) >= 2, f"outline retrieval collapsed to {sources}"


# --------------------------------------------------------------------------- #
# Per-file retrieval coverage across EVERY genre pack
# --------------------------------------------------------------------------- #


_ALL_PACK_DIRS = sorted(
    p for p in _CANON_SYSTEM_ROOT.iterdir()
    if p.is_dir() and p.name != "StoryDepth"
)


def _sections_with_body(
    path: Path, *, limit: int = 8, min_body: int = 80
) -> list[tuple[str, str]]:
    """``(heading, probe)`` pairs: a query and text that must come back with it.

    ``probe`` is a distinctive line from the section's own BODY, not its heading.
    Asserting on the body is what makes the test meaningful: the assembled block
    always carries a ``<!-- source: <file> -->`` header, so matching the file
    name alone passes even when the file is truncated to its first few hundred
    chars and the queried section never actually arrives.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    matches = list(re.finditer(r"^(#{2,4})\s+(.+)$", text, re.MULTILINE))
    out: list[tuple[str, str]] = []
    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        if len(heading) <= 12:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[m.end():end]
        probe = next(
            (
                line.strip()
                for line in body.splitlines()
                if len(line.strip()) >= min_body
                and set(line.strip()) - set("|-: ")
            ),
            "",
        )
        if probe:
            out.append((heading, probe[:min_body]))
    if len(out) <= limit:
        return out
    # Sample EVENLY across the document, never just the first N sections. A
    # truncation regression kills the TAIL of a file first, so probing only the
    # opening sections is exactly the blind spot that let the unsplit-chunk bug
    # survive: the head of the winning file always arrived, the rest never did.
    step = len(out) / limit
    return [out[int(i * step)] for i in range(limit)]


def _first_code(pack_dir: Path) -> str:
    """The first author-style code shipped by ``pack_dir`` (or "")."""
    for candidate in sorted((pack_dir / "Author Style").glob("[[]*[]]*.md")):
        m = re.match(r"\[([A-Z0-9]+)\]", candidate.name)
        if m:
            return m.group(1)
    return ""


@pytest.mark.parametrize("pack_dir", _ALL_PACK_DIRS, ids=lambda p: p.name)
def test_every_rag_file_is_retrievable_by_its_own_headings(pack_dir: Path):
    """Being *indexed* is not the same as being *reachable*.

    Before the chunk splitter each file was one chunk, so a query could only ever
    surface whichever single document won the whole budget — the rest of the pack
    was indexed and permanently unreachable. This walks every file the RAG channel
    claims to carry and asserts it actually comes back when queried with its OWN
    section headings. A file that cannot be retrieved by its own headings is dead
    weight, and this fails instead of letting it rot silently.
    """
    style = _first_code(pack_dir)
    ws = _workspace(
        genre=pack_dir.name.lower().replace(" ", "_"),
        pack=f"system/{pack_dir.name}",
        style=style,
        wb=style,
    )
    loop = LLMAutoNovelLoop(client=_CaptureClient())
    chunks = loop._canon_chunks(ws)
    if not chunks:
        pytest.skip(f"{pack_dir.name} contributes no RAG chunks")

    rag_files = sorted(loop._system_canon(ws)["rag"])
    checked = 0
    unreachable: list[str] = []
    for path in rag_files:
        sections = _sections_with_body(path)
        if not sections:
            continue
        checked += 1
        hits = sum(
            1
            for heading, probe in sections
            if probe
            in loop._retrieve_chunks(chunks, heading, max_chars=6000, chapter=1)
        )
        # A MAJORITY of the sampled sections must come back, not just one. With
        # ``any()`` a file that only ever returns its opening section counted as
        # "reachable", which is exactly the unsplit-chunk behaviour this guards
        # against: the head of the document always arrives, the rest never does.
        if hits * 2 <= len(sections):
            unreachable.append(
                f"{path.name} ({hits}/{len(sections)} sections)"
            )

    assert checked, f"{pack_dir.name}: no file offered a testable section"
    assert not unreachable, (
        f"{pack_dir.name}: {len(unreachable)}/{checked} RAG file(s) never return "
        f"their own section BODY when queried by that section's heading: "
        f"{unreachable}"
    )
