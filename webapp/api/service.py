"""Service layer — bridges the HTTP API to the NovelKit tool registry.

Everything the API does goes through the Orchestrator dispatch seam
(``delegate.delegate_tool``) so the web surface is hub-and-spoke just like the
CLI and cron. The service owns:

- novel workspace discovery + creation under a configurable root,
- per-novel pipeline state persistence (a JSON file standing in for the Hermes
  session store), and
- thin wrappers that delegate to ``novelkit_pipeline`` / ``novelkit_sync`` and
  read migration coverage.

No business logic is re-implemented here — it lives in the tools/plugins.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import re
import shutil
import sys
import threading
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

# --------------------------------------------------------------------------- #
# Make the novelkit-hermes package importable regardless of CWD.
# --------------------------------------------------------------------------- #

PACKAGE_ROOT = Path(__file__).resolve().parents[2]  # novelkit-hermes/
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))


def _tailieu_dir() -> Path:
    """Quick-suggest markdown corpus (hatgiong, MC, PD, …).

    Shipped inside the repo for Docker/Render. Falls back to the legacy sibling
    ``../tailieu`` path for local monorepo checkouts that still use it.
    """
    in_repo = PACKAGE_ROOT / "tailieu"
    if in_repo.is_dir():
        return in_repo
    legacy = PACKAGE_ROOT.parent / "tailieu"
    return legacy if legacy.is_dir() else in_repo

import bootstrap  # noqa: E402  — importing brings the whole tool surface online
from delegate import available_tools, delegate_tool  # noqa: E402
from tools.novelkit_pipeline_tool import ARC_SIZE, PipelineEngine  # noqa: E402
from tools.novelkit_pipeline_state_store import (  # noqa: E402
    PIPELINE_STATE_REL_PATH,
    PipelineStateConflict,
    PipelineStateDigestError,
    PipelineStateStore,
)
from webapp.db.models import Novel, User  # noqa: E402

# Bring every novelkit_* tool + plugin online at import time.
bootstrap.load_all()

#: Root that holds novel workspaces. Override with NOVELKIT_WORKSPACE_ROOT.
WORKSPACE_ROOT = Path(
    os.environ.get("NOVELKIT_WORKSPACE_ROOT", PACKAGE_ROOT / "workspaces")
).resolve()

SCHEDULE_CONFIG_PATH = PACKAGE_ROOT / "config" / "schedule.json"
PROVIDER_CONFIG_PATH = PACKAGE_ROOT / "config" / "provider.json"

#: Pipeline state lives beside the novel's logs (session-store stand-in).
PIPELINE_STATE_REL = PIPELINE_STATE_REL_PATH

_NOVEL_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
_CHAPTER_FILE_RE = re.compile(r"chapter_(\d+)\.md$", re.IGNORECASE)


#: In-process locks, one per novel name. Guards the read-modify-write of the
#: pipeline state within a single Uvicorn worker.
_NOVEL_LOCKS: dict[str, threading.Lock] = {}
_NOVEL_LOCKS_GUARD = threading.Lock()


def _novel_lock(name: str) -> threading.Lock:
    with _NOVEL_LOCKS_GUARD:
        lock = _NOVEL_LOCKS.get(name)
        if lock is None:
            lock = threading.Lock()
            _NOVEL_LOCKS[name] = lock
        return lock


class RunBusyError(Exception):
    """Raised when a novel already has a pipeline run in progress."""


@contextlib.contextmanager
def _novel_run_lock(name: str, path: Path):
    """Acquire the per-novel run lock (in-process + cross-process).

    Combines a :class:`threading.Lock` (serialises requests inside one worker)
    with an ``fcntl`` advisory lock on ``logs/.run.lock`` (serialises across
    separate processes — e.g. a CLI run racing the web UI). Both are acquired
    non-blocking; a contended lock raises :class:`RunBusyError` so the caller can
    return ``alreadyRunning`` instead of corrupting shared state.
    """
    thread_lock = _novel_lock(name)
    if not thread_lock.acquire(blocking=False):
        raise RunBusyError(name)
    # Everything past the acquire runs under try/finally. Opening the lock file
    # can fail for reasons that have nothing to do with a concurrent run (full
    # disk, read-only mount, permissions); when it did so outside the guard the
    # thread lock was never released, so the novel reported busy until the
    # process restarted — surfacing as a "Bước kế tiếp" button that does nothing.
    fh = None
    try:
        lock_path = path / "logs" / ".run.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fh = open(lock_path, "w", encoding="utf-8")
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RunBusyError(name) from exc
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    finally:
        if fh is not None:
            fh.close()
        thread_lock.release()


class ServiceError(Exception):
    """Raised for client-correctable problems (mapped to 4xx in the API)."""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    """Atomic JSON write: write a sibling temp file, fsync, then ``os.replace``.

    ``os.replace`` is atomic on the same filesystem, so a crash or a colliding
    writer can never leave a half-written (truncated) file behind — readers see
    either the old file or the fully-written new one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
    finally:
        with contextlib.suppress(OSError):
            if tmp.exists():
                tmp.unlink()


def _validate_name(name: str) -> str:
    if not _NOVEL_NAME_RE.match(name or ""):
        raise ServiceError(
            "Invalid novel name: use lowercase letters, digits, '-' or '_' "
            "(max 64 chars).",
            422,
        )
    return name


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #


class NovelKitService:
    """Stateless-over-the-filesystem facade the API routes call."""

    def __init__(self, workspace_root: Path = WORKSPACE_ROOT):
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)

    # ---- meta ----
    def tools(self) -> list[str]:
        return available_tools()

    def schedule(self) -> Any:
        if not SCHEDULE_CONFIG_PATH.exists():
            return {"jobs": []}
        return _read_json(SCHEDULE_CONFIG_PATH)

    def provider(self) -> Any:
        if not PROVIDER_CONFIG_PATH.exists():
            return {}
        return _read_json(PROVIDER_CONFIG_PATH)

    def inventory_summary(self) -> dict[str, Any]:
        """Migration completeness summary (P10) — read-only."""
        from migration import inventory

        try:
            inv = inventory.build_inventory()
            return inv["summary"]
        except (FileNotFoundError, OSError):
            # Production images omit ``_novelkit_source``; serve the checked-in snapshot.
            cached = inventory.INVENTORY_JSON
            if cached.is_file():
                return _read_json(cached).get("summary", {})
            return {
                "total_files": 0,
                "must_keep_count": 0,
                "orphan_count": 0,
                "coverage_complete": True,
                "review_flag_count": 0,
            }

    # ---- novel workspace ----
    @staticmethod
    def _owned_lock_key(user: User, slug: str) -> str:
        return f"{user.id}:{slug}"

    def _novel_dir(self, name: str) -> Path:
        return self.workspace_root / _validate_name(name)

    def _unique_name(self, db: Session, user: User, base: str) -> str:
        """Return ``base`` or, if taken, ``base-2`` / ``base-3`` … (≤64 chars)."""
        base = _validate_name(base)
        taken = set(
            db.scalars(
                select(Novel.slug).where(Novel.owner_user_id == user.id)
            ).all()
        )
        candidate, i = base, 2
        while candidate in taken:
            suffix = f"-{i}"
            candidate = base[: 64 - len(suffix)] + suffix
            i += 1
        return candidate

    def _require_owned_novel(self, db: Session, user: User, slug: str) -> tuple[Novel, Path]:
        novel = db.scalar(
            select(Novel).where(
                Novel.owner_user_id == user.id,
                Novel.slug == slug,
            )
        )
        if novel is None:
            raise ServiceError(f"Novel not found: {slug}", 404)
        from .novel_paths import novel_disk_path

        path = novel_disk_path(novel)
        if not path.is_dir():
            raise ServiceError(f"Novel not found: {slug}", 404)
        return novel, path

    def _require_novel(self, name: str) -> Path:
        path = self._novel_dir(name)
        if not path.is_dir():
            raise ServiceError(f"Novel not found: {name}", 404)
        return path

    def list_novels(self, db: Session, user: User) -> list[dict[str, Any]]:
        from .novel_paths import novel_disk_path

        novels = db.scalars(
            select(Novel).where(Novel.owner_user_id == user.id).order_by(Novel.created_at.desc())
        ).all()
        out: list[dict[str, Any]] = []
        for novel in novels:
            path = novel_disk_path(novel)
            if not path.is_dir():
                # Keep an orphaned DB record visible if its local workspace was
                # moved or deleted, so the operator can diagnose the mismatch.
                out.append(
                    {
                        "name": novel.slug,
                        "title": novel.title or novel.slug,
                        "status": "missing",
                        "target_chapters": None,
                        "chapters_written": 0,
                        "dna_ready": False,
                    }
                )
                continue
            out.append(self._novel_brief(path, novel.slug))
        return out

    @staticmethod
    def _novel_title(path: Path, fallback_name: str) -> str:
        """Best-effort display title from PROJECT_DNA.md (falls back to slug)."""
        dna = path / "PROJECT_DNA.md"
        try:
            text = dna.read_text(encoding="utf-8")
        except OSError:
            return fallback_name
        m = re.search(r"^#\s*PROJECT_DNA\.md\s*[—-]\s*(.+)$", text, re.MULTILINE)
        if m and m.group(1).strip() and "[" not in m.group(1):
            return m.group(1).strip()
        m = re.search(r"\*\*Tên tác phẩm:\*\*\s*(.+)", text)
        if m and m.group(1).strip():
            return m.group(1).strip()
        return fallback_name

    @staticmethod
    def _dna_ready(path: Path) -> bool:
        """Whether PROJECT_DNA.md exists and carries a real logline.

        Writing must never start before the author has a PROJECT_DNA (the
        single source of truth). A file that is missing, empty, or whose
        logline is still a blank/placeholder marker is treated as not ready.
        """
        dna = path / "PROJECT_DNA.md"
        try:
            text = dna.read_text(encoding="utf-8")
        except OSError:
            return False
        m = re.search(r"Logline[^:\n]*:\*\*[ \t]*(.+)", text)
        if not m:
            return False
        logline = m.group(1).strip()
        if not logline:
            return False
        # Reject template placeholders / unfilled markers.
        if logline.startswith("[") or "Tự sinh" in logline or "pitch toàn truyện" in logline:
            return False
        return True

    def _novel_brief(self, path: Path, slug: str) -> dict[str, Any]:
        status = "idle"
        target_chapters: Optional[int] = None
        state_path = path / PIPELINE_STATE_REL
        if state_path.exists():
            try:
                state = _read_json(state_path)
                target_chapters = state.get("target_chapters")
            except (OSError, json.JSONDecodeError):
                pass
        snapshot_path = path / "logs" / "pipeline_status.json"
        if snapshot_path.exists():
            try:
                status = _read_json(snapshot_path).get("status", "idle")
            except (OSError, json.JSONDecodeError):
                pass
        return {
            "name": slug,
            "title": self._novel_title(path, slug),
            "status": status,
            "target_chapters": target_chapters,
            "chapters_written": self._count_chapters(path),
            "dna_ready": self._dna_ready(path),
        }

    @staticmethod
    def _count_chapters(path: Path) -> int:
        chapters_dir = path / "chapters"
        if not chapters_dir.is_dir():
            return 0
        return sum(1 for p in chapters_dir.glob("chapter_*.md") if p.is_file())

    @staticmethod
    def chapter_file_from_path(path: Path, chapter: int) -> Path | None:
        """Resolve a chapter file by numeric chapter index."""
        chapters_dir = path / "chapters"
        if not chapters_dir.is_dir():
            return None
        for cp in chapters_dir.glob("chapter_*.md"):
            if not cp.is_file():
                continue
            match = _CHAPTER_FILE_RE.search(cp.name)
            if not match:
                continue
            if int(match.group(1)) == chapter:
                return cp
        return None

    def chapters_from_path(
        self, path: Path, *, max_chapter: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Build chapter metadata from a novel workspace path."""
        out: list[dict[str, Any]] = []
        chapters_dir = path / "chapters"
        if not chapters_dir.is_dir():
            return out
        for cp in sorted(chapters_dir.glob("chapter_*.md")):
            m = _CHAPTER_FILE_RE.search(cp.name)
            if not m:
                continue
            n = int(m.group(1))
            if max_chapter is not None and n > max_chapter:
                continue
            review = path / "reviews" / f"chapter_{n:03d}_review.md"
            committed = (path / ".commits" / f"chapter_{n:04d}.commit.json").exists()
            out.append(
                {
                    "chapter": n,
                    "has_review": review.exists(),
                    "committed": committed,
                    "words": len((cp.read_text(encoding="utf-8")).split()),
                }
            )
        out.sort(key=lambda x: x["chapter"])
        return out

    def dna_schema(self) -> dict[str, Any]:
        """Form schema (mirrors the PROJECT_DNA FILLABLE template) for the UI."""
        from . import dna_form

        return dna_form.schema()

    def generate_dna_fields(
        self,
        *,
        brief: str,
        genre: Optional[str] = None,
        title: Optional[str] = None,
        output_language: Optional[str] = None,
        output_language_custom: Optional[str] = None,
        db: Optional[Session] = None,
        user: Optional[User] = None,
    ) -> dict[str, Any]:
        """Quick Setup: let the LLM fill the DNA template from a short brief.

        Returns ``{"fields": {...}, "genre": <slug>}`` — the generated values are
        merged into the create form so the author can review/edit before saving.
        Requires a configured API key.
        """
        if not (brief or "").strip():
            raise ServiceError("Hãy nhập mô tả/ý tưởng truyện trước.", 422)
        from . import dna_form
        from provider.llm_client import LLMClient, LLMError
        from provider import settings as ps

        config = (
            ps.load_config(db=db, user_id=user.id)
            if db is not None and user is not None
            else ps.load_config()
        )
        if not config.configured:
            raise ServiceError(
                "Chưa cấu hình API key — mở Settings và nhập key để dùng Quick Setup.",
                400,
            )
        chosen = genre if genre in dna_form.GENRES else "xianxia"
        lang = output_language if output_language in dna_form.OUTPUT_LANGUAGE_CODES else "vi"
        lang_custom = (output_language_custom or "").strip()
        system, user = dna_form.generation_prompt(
            brief,
            chosen,
            title or "",
            output_language=lang,
            output_language_custom=lang_custom,
        )
        try:
            raw = LLMClient(config).complete(
                system=system, user=user, temperature=0.8, max_tokens=8000
            )
        except LLMError as exc:
            raise ServiceError(f"AI tự sinh thất bại: {exc}", 502)
        fields = dna_form.parse_generated(raw, chosen)
        # The model must never override the author's routing/style choices: genre,
        # secondary genre, hybrid ratio, and the three style codes are picked in
        # the create form and are authoritative. A model that invents them caused
        # a fabricated multi-value ``genre_secondary`` and a style (PT) that
        # overrode the author's pick (NC). Strip them so only the author's form
        # selection (merged client-side) survives.
        for _routing_key in dna_form._GEN_SKIP:
            fields.pop(_routing_key, None)
        fields["genre"] = chosen
        fields["output_language"] = lang
        if lang == "custom" and lang_custom:
            fields["output_language_custom"] = lang_custom
        if title and title.strip():
            fields.setdefault("title", title.strip())
        if not fields.get("title") and not fields.get("logline"):
            raise ServiceError(
                "AI không trả về nội dung hợp lệ. Thử lại hoặc viết mô tả rõ hơn.", 502
            )
        return {"fields": fields, "genre": chosen}

    def suggest_characters(self) -> dict[str, Any]:
        """Suggest character info for main character and antagonist from tailieu files."""
        import random
        tailieu_dir = _tailieu_dir()
        
        def clean_vietnamese(text: str) -> str:
            is_bullet = text.strip().startswith("-")
            content = text.strip()
            if is_bullet:
                content = content[1:].strip()
            content = re.sub(r'《[^》]*》', '', content)
            content = re.sub(r'（[^）]*）', '', content)
            content = re.sub(r'[\u4e00-\u9fa5]', '', content)
            content = re.sub(r'/\s*(?=\))', '', content)
            content = re.sub(r'/\s*$', '', content)
            text_cleaned = re.sub(r'\(\s*\)', '', content)
            text_cleaned = re.sub(r'\(([^)]+)\)', r'\1', text_cleaned)
            text_cleaned = text_cleaned.replace('*', '')
            text_cleaned = text_cleaned.strip().strip('-').strip('/').strip()
            text_cleaned = re.sub(r'[\s/]+', ' ', text_cleaned)
            content = text_cleaned.strip().strip('-').strip()
            return f"- {content}" if is_bullet else content

        # 1. Parse Main Characters from MC1.md, MC2.md, MC3.md
        mcs = []
        for fn in ["MC1.md", "MC2.md", "MC3.md"]:
            fp = tailieu_dir / fn
            if fp.is_file():
                try:
                    lines = fp.read_text(encoding="utf-8").split("\n")
                    for line in lines:
                        line = line.strip()
                        if line.startswith("|") and not "---" in line and not "Tên Nhân vật" in line and not "Tên nhân vật" in line:
                            cols = [c.strip() for c in line.split("|")]
                            if len(cols) >= 9:
                                cols = cols[1:-1]
                                mcs.append({
                                    "mc_name": clean_vietnamese(cols[0]),
                                    "mc_archetype": clean_vietnamese(cols[1]),
                                    "mc_traits": clean_vietnamese(cols[2]),
                                    "mc_motivation": clean_vietnamese(cols[3]),
                                    "mc_want": clean_vietnamese(cols[4]),
                                    "mc_need": clean_vietnamese(cols[5]),
                                    "mc_ghost": clean_vietnamese(cols[6]),
                                })
                except Exception:
                    pass

        # 2. Parse Antagonists from PD.md
        pds = []
        pd_fp = tailieu_dir / "PD.md"
        if pd_fp.is_file():
            try:
                sections = pd_fp.read_text(encoding="utf-8").split("\n## ")
                for sec in sections[1:]:
                    lines = sec.split("\n")
                    title_line = lines[0].strip()
                    title_line = re.sub(r'^\d+\.\s*', '', title_line)
                    title_line = re.sub(r'^(?:Tên\s*:\s*)?', '', title_line, flags=re.IGNORECASE)
                    antagonist_name = clean_vietnamese(title_line)
                    # Extract raw Vietnamese name of antagonist before Chinese / Book parts
                    base_name = title_line.split("/")[0].strip()
                    antagonist_base_name = clean_vietnamese(base_name)

                    traits = []
                    conflict_lines = []
                    in_traits = False
                    in_conflict = False

                    for line in lines[1:]:
                        line_strip = line.strip()
                        if line_strip.startswith("### Đặc điểm"):
                            in_traits = True
                            in_conflict = False
                            continue
                        elif line_strip.startswith("### Xung đột cốt lõi"):
                            in_traits = False
                            in_conflict = True
                            continue
                        elif line_strip.startswith("## ") or line_strip.startswith("---"):
                            in_traits = False
                            in_conflict = False

                        if in_traits:
                            if line_strip.startswith("-"):
                                traits.append(clean_vietnamese(line_strip))
                        elif in_conflict:
                            if line_strip:
                                conflict_lines.append(clean_vietnamese(line_strip))

                    pds.append({
                        "antagonist_name": antagonist_name,
                        "antagonist_base_name": antagonist_base_name,
                        "antagonist_traits": "\n".join(traits),
                        "antagonist_conflict": "\n".join(conflict_lines),
                    })
            except Exception:
                pass

        selected_mc = random.choice(mcs) if mcs else {}
        selected_pd = random.choice(pds) if pds else {}
        
        if selected_mc and selected_pd:
            new_mc_name = selected_mc.get("mc_name", "")
            
            # List of all MC names to replace in description fields
            mc_names_to_replace = ["Trần Trường Sinh", "Trường Sinh", "Ninh Khuyết", "Phạm Nhàn", "Hứa Nhạc"]
            if new_mc_name and new_mc_name not in mc_names_to_replace:
                mc_names_to_replace.append(new_mc_name)
            mc_names_to_replace.sort(key=len, reverse=True)
            
            # List of all antagonist names/shorthands to replace in description fields
            pd_names_to_replace = [
                "Bát Hoang Lục Hợp Duy Ngã Độc Tôn Công",
                "Thiên Hải Thánh Hậu",
                "Liên Sinh Tam Thập Nhị",
                "Tây Lăng Thần Điện",
                "Thương Sơn Hải",
                "Trần Bình Bình",
                "Diệp Khinh Mi",
                "Nhị Sư Huynh",
                "Nhị sư huynh",
                "Lý Mạn Mạn",
                "Trần Mỗ Mỗ",
                "Chu Độc Phu",
                "Khánh Đế",
                "Hạo Thiên",
                "Thành Hậu",
                "Thánh Hậu",
                "Liên Sinh",
                "Tây Lăng",
                "Độc Phu",
                "Diệp Tô",
                "Quân Thực",
                "Tô Ly",
                "Đường Đường",
                "Phu Tử"
            ]
            
            current_pd_base_name = selected_pd.get("antagonist_base_name", "")
            if current_pd_base_name and current_pd_base_name not in pd_names_to_replace:
                pd_names_to_replace.append(current_pd_base_name)
            pd_names_to_replace.sort(key=len, reverse=True)
            
            # Make a copy of selected_pd and selected_mc to return new modified instances
            selected_pd = dict(selected_pd)
            selected_mc = dict(selected_mc)
            
            # Remove antagonist_base_name from returning json to keep API payload clean
            if "antagonist_base_name" in selected_pd:
                del selected_pd["antagonist_base_name"]
            
            # 1. Clean MC description fields (replace any MC name with "Main chính")
            for key in ["mc_archetype", "mc_traits", "mc_motivation", "mc_want", "mc_need", "mc_ghost"]:
                if key in selected_mc and selected_mc[key]:
                    text = selected_mc[key]
                    for name in mc_names_to_replace:
                        text = text.replace(name, "Main chính")
                    selected_mc[key] = text
            
            # 2. Clean Antagonist description fields (replace MC names with "Main chính" and Antagonist names with "phản diện")
            for key in ["antagonist_traits", "antagonist_conflict"]:
                if key in selected_pd and selected_pd[key]:
                    text = selected_pd[key]
                    # Replace all MC names with "Main chính"
                    for name in mc_names_to_replace:
                        text = text.replace(name, "Main chính")
                    # Replace all antagonist names with "phản diện"
                    for name in pd_names_to_replace:
                        text = text.replace(name, "phản diện")
                    selected_pd[key] = text
        
        return {
            "mc": selected_mc,
            "antagonist": selected_pd,
        }

    def suggest_seed(self) -> dict[str, Any]:
        """Suggest seed info (logline, usp, theme, audience) from hatgiong.md."""
        import random
        tailieu_dir = _tailieu_dir()
        hatgiong_fp = tailieu_dir / "hatgiong.md"
        
        seeds = {
            "logline": [],
            "usp": [],
            "theme": [],
            "audience": []
        }
        
        if hatgiong_fp.is_file():
            try:
                content = hatgiong_fp.read_text(encoding="utf-8")
                sections = content.split("\n## ")
                for sec in sections:
                    lines = sec.split("\n")
                    header = lines[0].strip()
                    
                    key = None
                    if "1. LOGLINE" in header:
                        key = "logline"
                    elif "2. DẤU RIÊNG" in header or "2. USP" in header:
                        key = "usp"
                    elif "3. CHỦ ĐỀ" in header:
                        key = "theme"
                    elif "4. ĐỐI TƯỢNG" in header:
                        key = "audience"
                    
                    if key:
                        for line in lines[1:]:
                            line = line.strip()
                            if line:
                                match = re.match(r'^\d+\.\s*(.*)', line)
                                if match:
                                    item = match.group(1).strip()
                                    item = item.replace("**", "").replace("*", "")
                                    item = re.sub(r'[\u4e00-\u9fa5]', '', item)
                                    item = re.sub(r'《[^》]*》', '', item)
                                    item = re.sub(r'（[^）]*）', '', item)
                                    item = re.sub(r'\(\s*\)', '', item)
                                    item = re.sub(r'\(([^)]+)\)', r'\1', item)
                                    item = item.strip().strip('-').strip('/').strip()
                                    if item:
                                        seeds[key].append(item)
            except Exception:
                pass

        return {
            "logline": random.choice(seeds["logline"]) if seeds["logline"] else "",
            "usp": random.choice(seeds["usp"]) if seeds["usp"] else "",
            "theme": random.choice(seeds["theme"]) if seeds["theme"] else "",
            "audience": random.choice(seeds["audience"]) if seeds["audience"] else "",
        }

    def suggest_companions(self) -> dict[str, Any]:
        """Suggest companion info (artifact, spirit_beast, supporting_cast) from donghanh.md."""
        import random
        tailieu_dir = _tailieu_dir()
        donghanh_fp = tailieu_dir / "donghanh.md"
        
        comps = {
            "artifact": {"khởi đầu": [], "trung kỳ": [], "hậu kỳ": [], "kết thúc": []},
            "spirit_beast": {"khởi đầu": [], "trung kỳ": [], "hậu kỳ": [], "kết thúc": []},
            "supporting_cast": {"khởi đầu": [], "trung kỳ": [], "hậu kỳ": [], "kết thúc": []}
        }
        
        if donghanh_fp.is_file():
            try:
                content = donghanh_fp.read_text(encoding="utf-8")
                sections = content.split("\n## ")
                for sec in sections:
                    lines = sec.split("\n")
                    header = lines[0].strip()
                    
                    key = None
                    if "PHÁP BẢO" in header:
                        key = "artifact"
                    elif "LINH THÚ" in header:
                        key = "spirit_beast"
                    elif "DÀN NHÂN VẬT PHỤ" in header:
                        key = "supporting_cast"
                    
                    if key:
                        current_stage = None
                        for line in lines[1:]:
                            line_strip = line.strip()
                            if line_strip.startswith("### GIAI ĐOẠN KHỞI ĐẦU"):
                                current_stage = "khởi đầu"
                                continue
                            elif line_strip.startswith("### GIAI ĐOẠN TRUNG KỲ"):
                                current_stage = "trung kỳ"
                                continue
                            elif line_strip.startswith("### GIAI ĐOẠN HẬU KỲ"):
                                current_stage = "hậu kỳ"
                                continue
                            elif line_strip.startswith("### GIAI ĐOẠN KẾT THÚC"):
                                current_stage = "kết thúc"
                                continue
                            
                            if line_strip:
                                match = re.match(r'^\d+\.\s*(.*)', line_strip)
                                if match and current_stage:
                                    item = match.group(1).strip()
                                    item = item.replace("**", "").replace("*", "")
                                    item = item.replace("–", "-").replace("—", "-")
                                    item = re.sub(r'[\u4e00-\u9fa5]', '', item)
                                    item = re.sub(r'《[^》]*》', '', item)
                                    item = re.sub(r'（[^）]*）', '', item)
                                    item = re.sub(r'\(\s*\)', '', item)
                                    item = re.sub(r'\(([^)]+)\)', r'\1', item)
                                    item = item.strip().strip('-').strip('/').strip()
                                    if item:
                                        comps[key][current_stage].append(item)
            except Exception:
                pass

        selected = {}
        for key in ["artifact", "spirit_beast", "supporting_cast"]:
            parts = []
            for stage in ["khởi đầu", "trung kỳ", "hậu kỳ", "kết thúc"]:
                stage_list = comps[key][stage]
                if stage_list:
                    # Pick 1 or 2 items randomly from this stage list
                    num_to_choose = min(len(stage_list), random.randint(1, 2))
                    chosen_indices = sorted(random.sample(range(len(stage_list)), num_to_choose))
                    for idx in chosen_indices:
                        parts.append(f"- {stage_list[idx]}")
            selected[key] = "\n".join(parts)

        mc_names_to_replace = ["Trần Trường Sinh", "Trường Sinh", "Ninh Khuyết", "Phạm Nhàn", "Hứa Nhạc"]
        mc_names_to_replace.sort(key=len, reverse=True)

        pd_names_to_replace = [
            "Bát Hoang Lục Hợp Duy Ngã Độc Tôn Công", "Thiên Hải Thánh Hậu", "Liên Sinh Tam Thập Nhị",
            "Tây Lăng Thần Điện", "Thương Sơn Hải", "Trần Bình Bình", "Diệp Khinh Mi", "Nhị Sư Huynh",
            "Nhị sư huynh", "Lý Mạn Mạn", "Trần Mỗ Mỗ", "Chu Độc Phu", "Khánh Đế", "Hạo Thiên",
            "Thành Hậu", "Thánh Hậu", "Liên Sinh", "Tây Lăng", "Độc Phu", "Diệp Tô", "Quân Thực",
            "Tô Ly", "Đường Đường", "Phu Tử"
        ]
        pd_names_to_replace.sort(key=len, reverse=True)

        for k in selected:
            if selected[k]:
                text = selected[k]
                for name in mc_names_to_replace:
                    text = text.replace(name, "Main chính")
                for name in pd_names_to_replace:
                    text = text.replace(name, "phản diện")
                selected[k] = text

        return selected

    def suggest_cultivation(self, style_model: Optional[str] = None) -> dict[str, str]:
        """Suggest cultivation milestones from tuluyen.md, optionally aligned with style_model."""
        import random
        tailieu_dir = _tailieu_dir()
        tuluyen_fp = tailieu_dir / "tuluyen.md"
        
        GRANDMASTER_AUTHOR_MAP = {
            "VN": "Vong Ngữ",
            "NC": "Nhĩ Căn",
            "TD": "Tiêu Đỉnh",
            "DG": "Đường Gia Tam Thiếu",
            "TT": "Thiên Tàm Thổ Đậu",
            "CD": "Thần Đông",
            "TH": "Ngã Cật Tây Hồng Thị",
            "PL": "Phong Lăng Thiên Hạ",
            "OT": "Mực Thích Lặn Nước",
            "PT": "Phương Tưởng"
        }
        
        parsed_entries = []
        if tuluyen_fp.is_file():
            try:
                content = tuluyen_fp.read_text(encoding="utf-8")
                for line in content.splitlines():
                    line_strip = line.strip()
                    if not line_strip.startswith("|"):
                        continue
                    cols = [c.strip() for c in line_strip.split("|")]
                    if len(cols) < 6:
                        continue
                    # Ignore headers and separators
                    if "STT" in cols[1] or "---" in cols[1] or not cols[1].isdigit():
                        continue
                    
                    author = cols[3]
                    raw_route = cols[5]
                    items = re.split(r'<br\s*/?>', raw_route, flags=re.IGNORECASE)
                    cleaned_items = []
                    for item in items:
                        item = item.strip()
                        # remove bullet point symbols (like •, -, or *)
                        item = re.sub(r'^[•\-\*\s]+', '', item)
                        item = item.replace("**", "").replace("*", "")
                        item = item.replace("–", "-").replace("—", "-")
                        # remove Chinese characters
                        item = re.sub(r'[\u4e00-\u9fa5]', '', item)
                        item = re.sub(r'《[^》]*》', '', item)
                        item = re.sub(r'（[^）]*）', '', item)
                        item = re.sub(r'\(\s*\)', '', item)
                        item = re.sub(r'\(([^)]+)\)', r'\1', item)
                        item = item.strip().strip('-').strip('/').strip()
                        if item:
                            cleaned_items.append(f"- {item}")
                    if cleaned_items:
                        parsed_entries.append({
                            "author": author,
                            "timeline": "\n".join(cleaned_items)
                        })
            except Exception:
                pass
        
        if not parsed_entries:
            return {"cultivation_age_benchmarks": ""}
            
        candidates = []
        if style_model and style_model in GRANDMASTER_AUTHOR_MAP:
            target_author = GRANDMASTER_AUTHOR_MAP[style_model]
            candidates = [x["timeline"] for x in parsed_entries if x["author"] == target_author]
            
        if not candidates:
            candidates = [x["timeline"] for x in parsed_entries]
            
        selected_route = random.choice(candidates)
        
        # Generalize character names
        mc_names_to_replace = [
            "Hàn Lập", "Vương Lâm", "Tô Minh", "Mạnh Hạo", "Bạch Tiểu Thuần", "Trương Tiểu Phàm",
            "Đường Tam", "Tiêu Viêm", "Lâm Động", "Mục Trần", "Thần Nam", "Diệp Phàm", "Thạch Hạo",
            "Sở Phong", "Tiêu Thần", "Tần Vũ", "Lâm Lôi", "Đằng Thanh Sơn", "Quân Mạc Tà", "Sở Dương",
            "Trần Trường Sinh", "Trường Sinh", "Ninh Khuyết", "Phạm Nhàn", "Hứa Nhạc"
        ]
        mc_names_to_replace.sort(key=len, reverse=True)
        
        pd_names_to_replace = [
            "Bát Hoang Lục Hợp Duy Ngã Độc Tôn Công", "Thiên Hải Thánh Hậu", "Liên Sinh Tam Thập Nhị",
            "Tây Lăng Thần Điện", "Thương Sơn Hải", "Trần Bình Bình", "Diệp Khinh Mi", "Nhị Sư Huynh",
            "Nhị sư huynh", "Lý Mạn Mạn", "Trần Mỗ Mỗ", "Chu Độc Phu", "Khánh Đế", "Hạo Thiên",
            "Thành Hậu", "Thánh Hậu", "Liên Sinh", "Tây Lăng", "Độc Phu", "Diệp Tô", "Quân Thực",
            "Tô Ly", "Đường Đường", "Phu Tử"
        ]
        pd_names_to_replace.sort(key=len, reverse=True)
        
        for name in mc_names_to_replace:
            selected_route = selected_route.replace(name, "Main chính")
        for name in pd_names_to_replace:
            selected_route = selected_route.replace(name, "phản diện")
            
        return {"cultivation_age_benchmarks": selected_route}



    def create_novel(
        self,
        db: Session,
        user: User,
        *,
        name: str,
        fields: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Create a novel from form fields → render PROJECT_DNA → then init.

        The author's form input is written into the canonical PROJECT_DNA
        FILLABLE layout *first*; only then are planning docs bootstrapped and
        the pipeline seeded (Requirement: user fills the template, then init).
        """
        from . import dna_form

        fields = dict(fields or {})
        _validate_name(name)  # validates the slug first
        missing = dna_form.required_missing(fields)
        if missing:
            raise ServiceError(
                "Thiếu trường bắt buộc: " + ", ".join(missing), 422
            )
        style_errors = dna_form.normalize_style_selections(fields)
        if style_errors:
            raise ServiceError(
                "Mã phong cách không hợp lệ: " + "; ".join(style_errors), 422
            )

        # Auto-dedup the slug instead of failing on collision (name-2, name-3…).
        name = self._unique_name(db, user, name)
        novel = Novel(
            owner_user_id=user.id,
            slug=name,
            title=str(fields.get("title", "") or ""),
            logline=str(fields.get("logline", "") or ""),
            genre=str(fields.get("genre", "") or ""),
        )
        db.add(novel)
        db.commit()
        db.refresh(novel)

        from .novel_paths import ensure_novel_dir

        path = ensure_novel_dir(novel)
        (path / "chapters").mkdir(exist_ok=True)
        (path / "reviews").mkdir(exist_ok=True)
        (path / "memory").mkdir(exist_ok=True)
        (path / "logs").mkdir(exist_ok=True)

        # 1) Fill the PROJECT_DNA template from the form and write it, plus two
        #    sidecars: the raw form values (for lossless re-render / enrich) and
        #    the routing metadata (so technical keys never leak into prose/RAG).
        self._write_dna_bundle(path, name, fields)

        # 2) Bootstrap planning docs from that DNA (hub-and-spoke).
        try:
            delegate_tool("novelkit_dna", action="bootstrap_docs", project_path=str(path))
        except Exception:  # noqa: BLE001 — bootstrap is best-effort at creation
            pass

        # 2b) Build the derivative RAG index over the new canon (P5-safe).
        self._reindex_quiet(path)

        # 3) Seed a fresh pipeline state sized to the declared chapter count.
        engine = PipelineEngine.create(
            target_chapters=dna_form.target_chapters_of(fields),
            arc_size=ARC_SIZE,
            novel=name,
            mode="compass",
        )
        PipelineStateStore(path).save(engine.state)
        return self.novel_detail(db, user, name)

    @staticmethod
    def _reindex_quiet(path: Path) -> None:
        """Best-effort RAG reindex (never fails creation/enrich)."""
        try:
            from tools.novelkit_sync_tool import reindex

            reindex(path)
        except Exception:  # noqa: BLE001
            pass

    @staticmethod
    def _dna_meta(name: str, fields: dict[str, Any]) -> dict[str, Any]:
        """Routing metadata sidecar (genre/squad/canon/style) — never prose."""
        from . import dna_form

        genre = dna_form.resolve_genre(fields, where="service._dna_meta")
        secondary = dna_form._g(fields, "genre_secondary")
        secondary_style = dna_form._g(fields, "style_secondary")
        meta: dict[str, Any] = {
            "slug": name,
            "genre": "hybrid" if secondary else genre,
            "genre_primary": genre,
            "genre_secondary": secondary,
            "style_model": dna_form._g(fields, "style_model"),
            "style_secondary": secondary_style,
            "style_blend": secondary_style,
            "worldbuilding_guide": dna_form._g(fields, "worldbuilding_guide"),
            "sub_agents_squad": dna_form.derive_squad(genre),
            "canon_pack": f"system/{dna_form.canon_pack(genre)}",
            "target_chapters": dna_form.target_chapters_of(fields),
            "target_words_per_chapter": dna_form._g(
                fields, "target_words_per_chapter", "2500"
            ),
            "cultivation_speed": dna_form._g(fields, "cultivation_speed"),
            "status": "draft",
        }
        if secondary:
            meta["sub_agents_squad_secondary"] = dna_form.derive_squad(secondary)
            meta["canon_pack_secondary"] = f"system/{dna_form.canon_pack(secondary)}"
        return meta

    def _write_dna_bundle(
        self, path: Path, name: str, fields: dict[str, Any]
    ) -> None:
        """Persist the structured DNA and both deterministic derivatives."""
        from . import dna_form

        fields = dict(fields)
        # Heal a corrupted secondary genre (multi-value / unknown / == primary)
        # BEFORE style normalisation and rendering: a bad genre_secondary makes
        # every hybrid derivative (canon_pack_secondary, squad_secondary) invalid
        # and can never resolve a secondary style. Runs on every write so a novel
        # created before this fix self-heals on the next save/enrich.
        dna_form.normalize_secondary_genre(fields)
        style_errors = dna_form.normalize_style_selections(fields)
        if style_errors:
            raise ServiceError(
                "Mã phong cách không hợp lệ: " + "; ".join(style_errors), 422
            )
        rendered = dna_form.render_project_dna(fields)
        meta = self._dna_meta(name, fields)
        (path / "PROJECT_DNA.md").write_text(rendered, encoding="utf-8")
        _write_json(path / "PROJECT_DNA.meta.json", meta)
        # Write the canonical structured fields last: readers never observe a
        # new source sidecar before its two derivatives have been regenerated.
        _write_json(path / "PROJECT_DNA.fields.json", fields)

    def enrich_dna(
        self,
        db: Session,
        user: User,
        name: str,
        *,
        max_batches: int | None = None,
    ) -> dict[str, Any]:
        """AI-complete the deep PROJECT_DNA sections (legacy `enrich_dna` parity).

        Reads the saved form values, asks the LLM to fill the rich enrichment
        fields (Sections V/VII/IX/X/XI/XII/XIII/XIV), merges them, re-renders
        PROJECT_DNA.md and refreshes the planning docs. Idempotent-friendly:
        re-running overwrites with the latest enrichment.
        """
        _, path = self._require_owned_novel(db, user, name)
        from . import dna_form
        from provider.llm_client import LLMClient, LLMError
        from provider import settings as ps

        config = ps.load_config(db=db, user_id=user.id)
        if not config.configured:
            raise ServiceError("Chưa cấu hình API key để hoàn thiện DNA.", 400)

        fields_path = path / "PROJECT_DNA.fields.json"
        try:
            base = _read_json(fields_path)
        except (OSError, json.JSONDecodeError):
            base = {}
        if not base:
            raise ServiceError(
                "Không tìm thấy dữ liệu hạt giống (PROJECT_DNA.fields.json).", 409
            )

        # Self-heal a corrupted secondary genre BEFORE computing the enrich set:
        # a fabricated multi-value ``genre_secondary`` (e.g. "romance, meta_genre")
        # makes ``style_secondary`` a blocking field that can never be defaulted
        # (its secondary genre resolves to no style options), so enrich stalls on
        # "1 field remaining" forever. Persist the repair so every later read sees
        # the clean value.
        if dna_form.normalize_secondary_genre(base):
            self._write_dna_bundle(path, name, base)

        genre = dna_form.resolve_genre(base, where="service.enrich")
        genre_secondary = dna_form._g(base, "genre_secondary")
        client = LLMClient(config)
        enriched: dict[str, Any] = {}
        errors = 0
        import time

        def _run_batches(batches: list) -> int:
            """Fill ``enriched`` in place; return count of batches that failed."""
            failed = 0
            for subset in batches:
                subset_ids = {kk for kk, _ in subset}
                system, user = dna_form.enrich_prompt(base, subset)
                raw = ""
                for attempt in range(3):  # retries on transient gateway errors
                    try:
                        raw = client.complete(
                            system=system, user=user,
                            temperature=0.7, max_tokens=5000,
                        )
                        if raw:
                            break
                    except LLMError:
                        raw = ""
                    time.sleep(0.6 * (attempt + 1))  # backoff between attempts
                if not raw:
                    failed += 1
                    continue
                part = dna_form.parse_generated(
                    raw,
                    genre,
                    genre_secondary,
                )
                enriched.update({k: v for k, v in part.items() if k in subset_ids})
            return failed

        # Best-effort request set: every enrich field relevant to this genre
        # (incl. the genre's own optional section fields). Blocking set: the
        # subset whose absence should keep enrich "not done" — genre section
        # detail (spirit root, starting realm …) is requested but never wedges
        # the loop, since a model often omits that minor tail detail.
        all_enrich_ids = dna_form.enrich_ids_for_genre(genre)
        blocking_ids = set(dna_form.blocking_enrich_ids_for_genre(genre))

        missing = [
            k for k in all_enrich_ids
            if not str(base.get(k, "")).strip()
        ]
        requested: set[str] = set()
        if max_batches is not None:
            batches = dna_form.enrich_batches_for(missing)[: max(0, max_batches)]
            requested = {k for batch in batches for k, _ in batch}
            if batches:
                errors += _run_batches(batches)
        else:
            requested = set(missing)
            # First pass requests every empty field (blocking + best-effort
            # genre-section detail). Subsequent narrowing passes only retry the
            # *blocking* fields still missing: genre-section bullets (e.g.
            # mc_spirit_root, main_cultivation_method) render a suggestion
            # placeholder in the template and are author-fillable, so a model
            # omitting them must not burn extra passes or block completion.
            errors += _run_batches(dna_form.enrich_batches_for(missing))
            for _ in range(2):
                missing = [
                    k for k in all_enrich_ids
                    if k in blocking_ids
                    and not str(enriched.get(k, base.get(k, ""))).strip()
                ]
                if not missing:
                    break
                errors += _run_batches(dna_form.enrich_batches_for(missing))

        merged = {**base, **enriched}
        # Style/worldbuilding routing is NEVER model-generated. Author codes are
        # stable informational identifiers; worldbuilding codes select a guide.
        # Both remain deterministic so enrichment cannot rewrite user choices.
        style_defaults = {
            key for key in dna_form.STYLE_ROUTING_KEYS
            if not str(base.get(key, "")).strip()
        }
        if style_defaults:
            dna_form.apply_style_defaults(merged, only=style_defaults)
            for key in style_defaults:
                value = str(merged.get(key, "")).strip()
                if value and value != str(base.get(key, "")).strip():
                    enriched[key] = value

        if not enriched and max_batches is None:
            raise ServiceError(
                "Hoàn thiện DNA thất bại (provider không phản hồi). Thử lại.", 502
            )

        if merged != base:
            self._write_dna_bundle(path, name, merged)
            try:
                delegate_tool("novelkit_dna", action="bootstrap_docs",
                              project_path=str(path), force=True)
            except Exception:  # noqa: BLE001 — best effort
                pass
            self._reindex_quiet(path)
        # Completion is judged on blocking fields only. Genre-section detail
        # bullets are best-effort: the template renders a suggestion placeholder
        # for them and the author can fill them in the PROJECT_DNA tab, so a model
        # that omits them must not leave enrich permanently "incomplete".
        still_missing = sorted(
            k for k in all_enrich_ids
            if k in blocking_ids and not str(merged.get(k, "")).strip()
        )
        return {
            "enriched_fields": sorted(enriched.keys()),
            "count": len(enriched),
            "batches_failed": errors,
            "missing_fields": still_missing,
            "missing_count": len(still_missing),
            "done": len(still_missing) == 0,
        }

    def delete_novel(self, db: Session, user: User, name: str) -> dict[str, Any]:
        """Permanently remove a novel workspace (irreversible).

        Resolves the novel by ownership from the DB directly rather than via
        ``_require_owned_novel`` (which 404s when the workspace dir is missing):
        a novel whose on-disk workspace is gone — e.g. after a storage volume
        reset — must still be deletable from the UI, otherwise the ``missing``
        row surfaced in ``list_novels`` can never be cleaned up. ``rmtree`` is
        best-effort so an already-gone dir does not block the DB row removal.
        """
        from .novel_paths import novel_disk_path

        novel = db.scalar(
            select(Novel).where(
                Novel.owner_user_id == user.id,
                Novel.slug == name,
            )
        )
        if novel is None:
            raise ServiceError(f"Novel not found: {name}", 404)
        shutil.rmtree(novel_disk_path(novel).resolve(), ignore_errors=True)
        db.delete(novel)
        db.commit()
        return {"deleted": name}

    def read_artifact(self, db: Session, user: User, name: str, relpath: str) -> dict[str, Any]:
        """Read a step-produced artifact (chapter/outline/review/doc) as text.
        Used by the UI to let the author review what each AI step generated.
        The path is confined to the novel workspace (no traversal escape).
        """
        _, path = self._require_owned_novel(db, user, name)
        if not relpath:
            raise ServiceError("Missing artifact path.", 422)
        novel_root = path.resolve()
        target = (novel_root / relpath).resolve()
        if target != novel_root and novel_root not in target.parents:
            raise ServiceError("Refusing to read outside the novel workspace.", 400)
        if not target.is_file():
            raise ServiceError(f"Artifact not found: {relpath}", 404)
        try:
            text = target.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            raise ServiceError("Cannot read this artifact as text.", 415)
        return {"path": relpath, "text": text}

    def write_artifact(
        self, db: Session, user: User, name: str, relpath: str, text: str
    ) -> dict[str, Any]:
        """Write or update an existing artifact/planning document file in the novel workspace.
        Confined to the novel workspace (no traversal escape).
        """
        _, path = self._require_owned_novel(db, user, name)
        if not relpath:
            raise ServiceError("Missing artifact path.", 422)
        novel_root = path.resolve()
        target = (novel_root / relpath).resolve()
        if target != novel_root and novel_root not in target.parents:
            raise ServiceError("Refusing to write outside the novel workspace.", 400)

        if target == novel_root / "PROJECT_DNA.fields.json":
            try:
                fields = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ServiceError(
                    f"PROJECT_DNA.fields.json không phải JSON hợp lệ: {exc.msg}",
                    422,
                ) from exc
            if not isinstance(fields, dict):
                raise ServiceError(
                    "PROJECT_DNA.fields.json phải là một JSON object.", 422
                )
            self._write_dna_bundle(path, name, fields)
            self._reindex_quiet(path)
            return {
                "path": relpath,
                "success": True,
                "synced": [
                    "PROJECT_DNA.fields.json",
                    "PROJECT_DNA.md",
                    "PROJECT_DNA.meta.json",
                ],
            }
        
        # Make sure parent directories exist
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            target.write_text(text, encoding="utf-8")
        except OSError as e:
            raise ServiceError(f"Cannot write to this file: {str(e)}", 500)
        return {"path": relpath, "success": True}

    #: Placeholder a bootstrap file carries when its LLM call failed — the file
    #: is not real canon and can be regenerated from the Docs tab.
    _BOOTSTRAP_STUB_MARKER = "_(chờ AI bổ sung — chạy lại bước này)_"

    #: Top-level dirs/files surfaced in the "Tài liệu" tab (generated during writing).
    _DOC_GLOBS = (
        "PLAN.md",
        "GOAL_TRACKER.md",
        "database/**/*.md",
        "outlines/**/*.md",
        "memory/*.md",
    )

    def list_docs(self, db: Session, user: User, name: str) -> list[dict[str, Any]]:
        """List planning/worldbuilding docs generated during writing.

        Excludes chapters/reviews (their own tab) and PROJECT_DNA.md (its tab).
        Returns ``[{path, label, group, words}]`` sorted by path.
        """
        _, path = self._require_owned_novel(db, user, name)
        root = path.resolve()
        seen: set[Path] = set()
        out: list[dict[str, Any]] = []
        for pattern in self._DOC_GLOBS:
            for p in sorted(root.glob(pattern)):
                if not p.is_file() or p in seen:
                    continue
                seen.add(p)
                rel = p.relative_to(root).as_posix()
                group = rel.split("/")[0] if "/" in rel else "root"
                try:
                    text = p.read_text(encoding="utf-8")
                    words = len(text.split())
                except (OSError, UnicodeDecodeError):
                    text = ""
                    words = 0
                # A file still carrying the bootstrap stub marker (or empty) is
                # not real canon — the UI surfaces a "regenerate" button for it.
                is_stub = not text.strip() or self._BOOTSTRAP_STUB_MARKER in text
                out.append(
                    {
                        "path": rel,
                        "label": p.name,
                        "group": group,
                        "words": words,
                        "is_stub": is_stub,
                    }
                )
        return out

    def novel_detail(self, db: Session, user: User, name: str) -> dict[str, Any]:
        _, path = self._require_owned_novel(db, user, name)
        brief = self._novel_brief(path, name)
        state = self._load_state(path)
        snapshot = self._status_snapshot(path)
        doctor = self.doctor(db, user, name)
        return {
            **brief,
            "pipeline_status": snapshot,
            "ready_task": self._ready_task(state),
            "doctor": doctor,
            "dna": self._read_optional(path / "PROJECT_DNA.md"),
        }

    @staticmethod
    def _read_optional(path: Path) -> Optional[str]:
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return None

    def _status_snapshot(self, path: Path) -> Any:
        snap = path / "logs" / "pipeline_status.json"
        if snap.exists():
            try:
                return _read_json(snap)
            except (OSError, json.JSONDecodeError):
                return None
        return None

    @staticmethod
    def _ready_task(state: dict[str, Any]) -> Any:
        engine = PipelineEngine(_state_from_dict(state))
        task = engine.plan_next(claim=False)
        return task.to_dict() if task else None

    # ---- pipeline ops (delegate to the tool, persist state) ----
    @staticmethod
    def _assert_single_runtime(path: Path) -> None:
        """Refuse to operate on a workspace owned by the legacy runtime.

        The legacy ``_novelkit_source`` control plane stores state in a SQLite
        file (``.controlplane.sqlite3``); the Hermes runtime uses a JSON state
        file. If both live in one workspace, two runtimes would write divergent
        truth for the same novel. Fail loudly instead of clobbering it.
        """
        legacy = path / ".controlplane.sqlite3"
        if legacy.exists():
            raise ServiceError(
                "Workspace has legacy control-plane state "
                "(.controlplane.sqlite3). This novel belongs to the old runtime; "
                "the Hermes runtime will not write JSON state beside it. Migrate "
                "or remove the legacy state before running here.",
                409,
            )

    def _load_state(self, path: Path) -> dict[str, Any]:
        self._assert_single_runtime(path)
        store = PipelineStateStore(path)
        if not store.state_path.exists():
            raise ServiceError("Pipeline state missing; recreate the novel.", 409)
        try:
            return store.load_payload()
        except PipelineStateDigestError as exc:
            raise ServiceError(f"Pipeline state digest mismatch: {exc}", 409) from exc

    def _save_state(
        self,
        path: Path,
        state: dict[str, Any],
        *,
        expected_version: int | None = None,
    ) -> None:
        try:
            PipelineStateStore(path).save(state, expected_version=expected_version)
        except (PipelineStateConflict, PipelineStateDigestError) as exc:
            raise ServiceError(f"Pipeline state conflict: {exc}", 409) from exc

    def plan_next(self, db: Session, user: User, name: str, *, claim: bool = False) -> Any:
        _, path = self._require_owned_novel(db, user, name)
        lock_key = self._owned_lock_key(user, name)
        if not claim:
            # Read-only planning never mutates state, so it needs no lock.
            out = delegate_tool(
                "novelkit_pipeline", action="plan_next",
                state=self._load_state(path), claim=False,
            )
            return out["result"]
        with _novel_run_lock(lock_key, path):
            state = self._load_state(path)
            out = delegate_tool(
                "novelkit_pipeline", action="plan_next",
                state=state, claim=True,
            )
            self._save_state(path, out["state"], expected_version=state.get("state_version"))
            self._refresh_snapshot(path, out["state"])
            return out["result"]

    def record_result(
        self,
        db: Session,
        user: User,
        name: str,
        *,
        task_key: str,
        result: str,
        score: Optional[float] = None,
    ) -> Any:
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            state = self._load_state(path)
            out = delegate_tool(
                "novelkit_pipeline",
                action="record_result",
                state=state,
                task_key=task_key,
                result=result,
                score=score,
            )
            self._save_state(path, out["state"], expected_version=state.get("state_version"))
            self._refresh_snapshot(path, out["state"])
            return out["result"]

    def resume(self, db: Session, user: User, name: str) -> Any:
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            state = self._load_state(path)
            out = delegate_tool(
                "novelkit_pipeline", action="resume", state=state
            )
            self._save_state(path, out["state"], expected_version=state.get("state_version"))
            self._refresh_snapshot(path, out["state"])
            return out["result"]

    def recover(self, db: Session, user: User, name: str) -> Any:
        """Clear an open circuit breaker and release blocked tasks (operator valve).

        The UI's only exit from a wedged run: when repeated failures trip the
        breaker, every task parks as BLOCKED and nothing is ready, so neither
        resume nor plan-next can progress. This resets the breaker + releases
        blocked tasks back to retryable so the next run re-attempts them.
        """
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            state = self._load_state(path)
            out = delegate_tool(
                "novelkit_pipeline", action="recover", state=state
            )
            self._save_state(path, out["state"], expected_version=state.get("state_version"))
            self._refresh_snapshot(path, out["state"])
            return out["result"]

    def approve_chapter(self, db: Session, user: User, name: str, *, chapter: int) -> Any:
        """Manually pass a chapter the AI could not lift above the quality bar.

        The "Duyệt tay" valve: stamps ``human_approved`` onto the chapter's typed
        review JSON so the sync gate accepts the exact reviewed draft, then clears
        the breaker and releases blocked tasks so the run continues. The draft +
        rules validation in ``_load_typed_review`` still runs, so approval only
        applies to the reviewed draft under the current rules.
        """
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            # Ensure a valid human-approved review JSON exists for the CURRENT
            # draft so the sync gate passes. When the chapter is blocked at
            # self_check (before review ever ran) the file is absent — synthesise
            # one; when it exists, stamp the approval flag. Either way sync gets a
            # gate-passing review bound to the exact draft under current rules.
            # (A missing review is no longer a 404 — that was why "Duyệt tay"
            # did nothing when the block was at self_check.)
            # The approval marker is later eligible for RAG context. Keep it
            # Keep the local audit label non-identifying.
            approver = "local_operator"
            try:
                delegate_tool(
                    "novelkit_sync",
                    action="stamp_human_approval",
                    novel_path=str(path),
                    chapter=chapter,
                    approver=approver,
                )
            except FileNotFoundError as exc:
                raise ServiceError(
                    f"Chưa có bản thảo chương {chapter} để duyệt: {exc}", 404
                )
            # Force-pass the chapter's pre-sync gate tasks (self_check / review)
            # and clear the breaker so the run advances to sync and beyond. Sync
            # itself still runs (it promotes the draft into canon).
            state = self._load_state(path)
            out = delegate_tool(
                "novelkit_pipeline",
                action="approve_chapter",
                state=state,
                chapter=chapter,
            )
            self._save_state(path, out["state"], expected_version=state.get("state_version"))
            self._refresh_snapshot(path, out["state"])
            return {"approved": True, "chapter": chapter, "recover": out["result"]}

    def apply_run_command(
        self,
        db: Session,
        user: User,
        name: str,
        *,
        command_type: str,
        payload: Optional[dict[str, Any]] = None,
        expected_state_version: Optional[int] = None,
    ) -> dict[str, Any]:
        """Apply supported step-boundary commands to authoritative PipelineState."""
        _, path = self._require_owned_novel(db, user, name)
        if command_type not in {"pause", "resume", "cancel_after_step"}:
            return {"applied": False, "reason": "queued_only"}
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            state = self._load_state(path)
            current_version = state.get("state_version")
            if (
                expected_state_version is not None
                and current_version != expected_state_version
            ):
                raise ServiceError(
                    f"Command state_version conflict: expected "
                    f"{expected_state_version}, found {current_version}",
                    409,
                )
            engine = PipelineEngine(_state_from_dict(state))
            reason = str((payload or {}).get("reason") or command_type)
            if command_type in {"pause", "cancel_after_step"}:
                changed = engine.set_paused(True, reason=reason)
            else:
                changed = engine.set_paused(False)
                if engine.resume().in_progress_reset:
                    changed = True
            if changed:
                next_state = engine.state.to_dict()
                self._save_state(
                    path,
                    next_state,
                    expected_version=state.get("state_version"),
                )
                self._refresh_snapshot(path, next_state)
            return {
                "applied": changed,
                "state_version": engine.state.to_dict()["state_version"],
                "paused": engine.state.creative.paused,
            }

    def _refresh_snapshot(self, path: Path, state: dict[str, Any]) -> None:
        try:
            PipelineStateStore(path).write_status_projection(state)
        except Exception:  # noqa: BLE001 — snapshot is advisory
            pass

    def rolling_seed(self, db: Session, user: User, name: str) -> Any:
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            state = self._load_state(path)
            out = delegate_tool(
                "novelkit_pipeline", action="rolling_seed",
                state=state,
            )
            self._save_state(path, out["state"], expected_version=state.get("state_version"))
            return out["result"]

    # ---- sync + doctor ----
    def sync(self, db: Session, user: User, name: str, *, chapter: int) -> Any:
        _, path = self._require_owned_novel(db, user, name)
        return delegate_tool(
            "novelkit_sync", action="commit", novel_path=str(path), chapter=chapter
        )

    def doctor(self, db: Session, user: User, name: str) -> Any:
        _, path = self._require_owned_novel(db, user, name)
        return delegate_tool("novelkit_sync", action="doctor", novel_path=str(path))

    # ---- long-form GA surface (NovelCLI): compass / steer / diag / reminder ----
    def longform_status(self, db: Session, user: User, name: str) -> dict[str, Any]:
        """Read-only aggregate for the NovelCLI panel (Req 1,8,9,10,14).

        Degrades gracefully: feature flags default OFF, and compass/arc-map/
        state are returned as ``None``/empty when the artifacts don't exist yet,
        so the panel never errors on a novel that hasn't opted into long-form.
        """
        _, path = self._require_owned_novel(db, user, name)
        from tools.novelkit_longform_config import load_config

        cfg = load_config(path)
        flags = cfg.get("flags", {})
        thresholds = {k: v for k, v in cfg.items() if k != "flags"}

        mode: Optional[str] = None
        pending_steer: Any = None
        reminder: Optional[str] = None
        stop_guard_info: Optional[dict[str, Any]] = None
        try:
            state = self._load_state(path)
        except ServiceError:
            state = None
        if state is not None:
            creative = state.get("creative") or {}
            mode = creative.get("mode")
            pending_steer = creative.get("pending_steer")
            try:
                from tools.novelkit_reminder import build_reminder, stop_guard

                ps = _state_from_dict(state)
                reminder = build_reminder(ps)
                blocked, reason = stop_guard(
                    ps, max_stop_blocks=int(thresholds.get("MAX_STOP_BLOCKS", 3))
                )
                stop_guard_info = {"blocked": blocked, "reason": reason}
            except Exception:  # noqa: BLE001 — reminder/guard are advisory
                pass

        compass = delegate_tool(
            "novelkit_compass", action="read_compass", novel_path=str(path)
        )
        arc_map = delegate_tool(
            "novelkit_compass", action="read_arc_map", novel_path=str(path)
        )
        return {
            "mode": mode,
            "flags": flags,
            "thresholds": thresholds,
            "compass": compass,
            "arc_map": arc_map,
            "pending_steer": pending_steer,
            "reminder": reminder,
            "stop_guard": stop_guard_info,
        }

    def steer(self, db: Session, user: User, name: str, *, text: str) -> dict[str, Any]:
        """Apply a realtime steer (Req 9). Mutates state under the novel lock."""
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            state = self._load_state(path)
            out = delegate_tool(
                "novelkit_steer", action="apply",
                novel_path=str(path), text=text, state=state,
            )
            self._save_state(
                path, out["state"], expected_version=state.get("state_version")
            )
            self._refresh_snapshot(path, out["state"])
            return {
                "route": out["route"],
                "affected_chapters": out["affected_chapters"],
                "steer_id": out["steer_id"],
                "applied": out["applied"],
                "executed": out.get("executed", {}),
            }

    def diagnostics(
        self, db: Session, user: User, name: str, *, redact: bool = False
    ) -> Any:
        """Creative-health diagnostics (Req 10). Read-only, never mutates."""
        _, path = self._require_owned_novel(db, user, name)
        return delegate_tool(
            "novelkit_diagnostics", action="diagnose",
            novel_path=str(path), redact=redact,
        )

    def compass_migrate(
        self, db: Session, user: User, name: str,
        *, current_chapter: int, target_chapters: int,
    ) -> Any:
        """Bootstrap compass.md + arc_map.json for an in-progress novel (Req 11.4)."""
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            return delegate_tool(
                "novelkit_compass", action="migrate_to_compass",
                novel_path=str(path),
                current_chapter=current_chapter,
                target_chapters=target_chapters,
            )

    # ---- chapter content (read) ----
    def chapters(self, db: Session, user: User, name: str) -> list[dict[str, Any]]:
        _, path = self._require_owned_novel(db, user, name)
        return self.chapters_from_path(path)

    def chapter_content(self, db: Session, user: User, name: str, chapter: int) -> dict[str, Any]:
        _, path = self._require_owned_novel(db, user, name)
        ch = self.chapter_file_from_path(path, chapter)
        rv = path / "reviews" / f"chapter_{chapter:03d}_review.md"
        if ch is None or not ch.exists():
            raise ServiceError(f"Chapter {chapter} not found.", 404)
        return {
            "chapter": chapter,
            "text": ch.read_text(encoding="utf-8"),
            "review": rv.read_text(encoding="utf-8") if rv.exists() else None,
        }

    # ---- creative tool passthroughs (analysis helpers for the editor) ----
    def analyze_ai_flavor(self, text: str) -> Any:
        return delegate_tool("novelkit_ai_flavor", text=text)

    def language_guard(self, text: str, genre: str, secondary: Optional[str] = None) -> Any:
        return delegate_tool(
            "novelkit_language_guard", text=text, genre=genre, secondary_genre=secondary
        )

    # ---- provider settings (LLM API key) ----
    def provider_settings(
        self, db: Optional[Session] = None, user: Optional[User] = None
    ) -> dict[str, Any]:
        from provider import settings as ps

        return (
            ps.public_view(db=db, user_id=user.id)
            if db is not None and user is not None
            else ps.public_view()
        )

    def save_provider_settings(
        self,
        db: Optional[Session] = None,
        user: Optional[User] = None,
        *,
        provider: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> dict[str, Any]:
        from provider import settings as ps

        ps.save_config(
            db=db,
            user_id=user.id if user is not None else None,
            provider=provider,
            base_url=base_url,
            model=model,
            api_key=api_key,
        )
        return (
            ps.public_view(db=db, user_id=user.id)
            if db is not None and user is not None
            else ps.public_view()
        )

    def test_provider(
        self,
        db: Optional[Session] = None,
        user: Optional[User] = None,
        *,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ) -> dict[str, Any]:
        from provider.llm_client import LLMClient, LLMConfig
        from provider import settings as ps

        saved = (
            ps.load_config(db=db, user_id=user.id)
            if db is not None and user is not None
            else ps.load_config()
        )
        probe_key = api_key.strip() if api_key else saved.api_key
        config = LLMConfig(
            base_url=base_url if base_url is not None else saved.base_url,
            model=model if model is not None else saved.model,
            api_key=probe_key,
            temperature=saved.temperature,
            max_tokens=saved.max_tokens,
            timeout=saved.timeout,
        )
        if not config.configured:
            raise ServiceError("No API key configured. Save it in Settings first.", 400)
        return LLMClient(config).test_connection()

    # ---- real AI run: auto-advance the pipeline via the LLM loop ----
    # ---- real AI run: lock-guarded public entrypoints ----
    def run(
        self,
        db: Session,
        user: User,
        name: str,
        *,
        max_steps: int = 12,
        stop_after_chapters: Optional[int] = None,
    ) -> dict[str, Any]:
        """Lock-guarded wrapper around :meth:`_run_locked`.

        Serialises the whole read-modify-write of pipeline state so two
        concurrent runs (two tabs, a double click, or a CLI racing the UI)
        cannot clobber each other. A contended novel raises :class:`RunBusyError`,
        which the API maps to ``alreadyRunning`` instead of corrupting state.
        """
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            return self._run_locked(
                path,
                max_steps=max_steps,
                stop_after_chapters=stop_after_chapters,
                db=db,
                user=user,
            )

    def run_step(self, db: Session, user: User, name: str) -> dict[str, Any]:
        """Lock-guarded wrapper around :meth:`_run_step_locked`."""
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            return self._run_step_locked(path, db=db, user=user)

    def regenerate_doc(
        self, db: Session, user: User, name: str, *, relpath: str
    ) -> dict[str, Any]:
        """Regenerate ONE stubbed bootstrap canon file on demand.

        The fallback for the field report: a bootstrap file left on the
        ``_(chờ AI bổ sung — chạy lại bước này)_`` stub (e.g. after a transient
        provider timeout) can be rebuilt from the UI without re-running the whole
        pipeline. Re-runs the owning bootstrap command's ``worldbuild`` stage,
        which is idempotent — it skips files that already hold real content and
        only regenerates the still-stubbed ones.
        """
        _, path = self._require_owned_novel(db, user, name)
        with _novel_run_lock(self._owned_lock_key(user, name), path):
            return self._regenerate_doc_locked(path, relpath=relpath, db=db, user=user)

    def _regenerate_doc_locked(
        self,
        path: Path,
        *,
        relpath: str,
        db: Optional[Session] = None,
        user: Optional[User] = None,
    ) -> dict[str, Any]:
        from integrations.autonovel.llm_loop import _BOOTSTRAP_FILES

        # Reverse-map the file to the bootstrap command that owns it.
        command = next(
            (
                cmd
                for cmd, targets in _BOOTSTRAP_FILES.items()
                if any(rel == relpath for rel, _ in targets)
            ),
            None,
        )
        if command is None:
            raise ServiceError(
                f"'{relpath}' không phải tài liệu nền có thể tạo lại tự động.", 400
            )

        from provider.llm_client import LLMClient, LLMError
        from provider import settings as ps

        config = (
            ps.load_config(db=db, user_id=user.id)
            if db is not None and user is not None
            else ps.load_config()
        )
        if not config.configured:
            raise ServiceError(
                "No LLM API key configured — open Settings and add your key.", 400
            )

        from integrations.autonovel.adapter import AutoNovelWorkspace, LoopStage, LoopStep
        from integrations.autonovel.llm_loop import LLMAutoNovelLoop

        # Force this one file to regenerate: clear its stub so the idempotent
        # skip in ``worldbuild`` does not treat the placeholder as real content.
        target = path / relpath
        try:
            existing = target.read_text(encoding="utf-8")
        except OSError:
            existing = ""
        if self._BOOTSTRAP_STUB_MARKER in existing:
            target.write_text("", encoding="utf-8")

        step = LoopStep(
            task_key=f"bootstrap.regenerate:{relpath}",
            stage=LoopStage.WORLDBUILD,
            phase="1",
            command=command,
            agent_role="World Builder",
            chapter=None,
            arc=None,
            input_paths=("PROJECT_DNA.md",),
            output_paths=(),
            context_query=None,
        )
        workspace = AutoNovelWorkspace(root=path)
        loop = LLMAutoNovelLoop(client=LLMClient(config))
        try:
            loop.worldbuild(step, workspace)
        except LLMError as exc:
            raise ServiceError(f"Tạo lại tài liệu thất bại: {exc}", 502)

        self._reindex_quiet(path)
        text = self._read_optional(target) or ""
        still_stub = (not text.strip()) or self._BOOTSTRAP_STUB_MARKER in text
        return {
            "path": relpath,
            "regenerated": not still_stub,
            "is_stub": still_stub,
            "words": len(text.split()),
        }

    @staticmethod
    def _release_stale_pipeline_claims(engine: Any) -> bool:
        """Reset orphaned in-progress tasks after a crashed or aborted run."""
        before = engine.state.state_version
        engine.resume()
        return engine.state.state_version != before

    def _finalize_pipeline_state(self, path: Path, engine: Any) -> None:
        expected_version = engine.state.state_version
        self._release_stale_pipeline_claims(engine)
        state = engine.state.to_dict()
        self._save_state(path, state, expected_version=expected_version)
        self._refresh_snapshot(path, state)

    # Safety ceiling per chapter when running in "write N chapters" mode, so a
    # chapter that keeps failing review can never burn the budget forever. A
    # clean chapter is ~5 steps; retries + up to MAX_REWRITE_CYCLES rewrites
    # (review+sync ×2) push a hard chapter toward ~11, so 20/chapter is a
    # generous ceiling that still stops a truly stuck run.
    _STEPS_PER_CHAPTER_CEILING = 20

    def _run_locked(
        self,
        path: Path,
        *,
        max_steps: int = 12,
        stop_after_chapters: Optional[int] = None,
        db: Optional[Session] = None,
        user: Optional[User] = None,
    ) -> dict[str, Any]:
        """Drive the novel's existing pipeline with the real LLM creative loop.

        Uses the persisted pipeline state (does NOT reset it). By default runs up
        to ``max_steps`` stages. When ``stop_after_chapters`` is set, it instead
        runs until that many chapters finish syncing this run, with a derived
        step ceiling (``_STEPS_PER_CHAPTER_CEILING`` per chapter) as a hard
        safety cap. Saves the advanced state back. Requires a configured API key.
        """
        if not self._dna_ready(path):
            raise ServiceError(
                "Chưa có PROJECT_DNA hợp lệ. Hãy tạo PROJECT_DNA (bước đầu tiên) "
                "trước khi sáng tác.",
                409,
            )
        from provider.llm_client import LLMClient, LLMError
        from provider import settings as ps

        config = (
            ps.load_config(db=db, user_id=user.id)
            if db is not None and user is not None
            else ps.load_config()
        )
        if not config.configured:
            raise ServiceError(
                "No LLM API key configured — open Settings and add your key.", 400
            )

        from integrations.autonovel.adapter import AutoNovelAdapter, AutoNovelWorkspace
        from integrations.autonovel.llm_loop import LLMAutoNovelLoop

        store = PipelineStateStore(path)
        state = self._load_state(path)
        engine = PipelineEngine(_state_from_dict(state))
        if self._release_stale_pipeline_claims(engine):
            store.save(engine.state, expected_version=state.get("state_version"))
        workspace = AutoNovelWorkspace(root=path)
        loop = LLMAutoNovelLoop(client=LLMClient(config))
        adapter = AutoNovelAdapter(engine, loop, workspace, state_store=store)

        error: Optional[str] = None
        # Accumulate across seed→run cycles so one click keeps writing until the
        # budget runs out or the target is reached (no manual "rolling seed").
        merged: dict[str, Any] = {
            "steps": [],
            "tasks_completed": 0,
            "chapters_drafted": 0,
            "chapters_synced": 0,
            "blocked": False,
            "breaker_open": False,
            "final_status": None,
            "stopped_reason": None,
        }
        # Chapter mode: run until N chapters sync, capped by a derived step
        # ceiling so a stuck chapter can't loop forever. Step mode: original
        # fixed step budget. Both accumulate across seed→run cycles so one click
        # keeps writing until the goal or the ceiling is hit.
        chapter_mode = stop_after_chapters is not None and stop_after_chapters > 0
        step_ceiling = (
            stop_after_chapters * self._STEPS_PER_CHAPTER_CEILING
            if chapter_mode
            else max_steps
        )
        try:
            remaining = step_ceiling
            while remaining > 0:
                run_kwargs: dict[str, Any] = {"max_steps": remaining}
                if chapter_mode:
                    run_kwargs["max_chapters"] = (
                        stop_after_chapters - merged["chapters_synced"]
                    )
                report = adapter.run(**run_kwargs).to_dict()
                merged["steps"].extend(report["steps"])
                merged["tasks_completed"] += report["tasks_completed"]
                merged["chapters_drafted"] += report["chapters_drafted"]
                merged["chapters_synced"] += report["chapters_synced"]
                merged["blocked"] = merged["blocked"] or report["blocked"]
                merged["breaker_open"] = report["breaker_open"]
                merged["final_status"] = report["final_status"]
                merged["stopped_reason"] = report["stopped_reason"]
                remaining = step_ceiling - len(merged["steps"])
                if report["breaker_open"] or report["stopped_reason"] == "max_steps":
                    break
                # Reached the requested chapter count → done for this run.
                if chapter_mode and merged["chapters_synced"] >= stop_after_chapters:
                    break
                # Drained: try to seed the next chapter window and continue.
                if report["stopped_reason"] == "drained":
                    before_seed_version = engine.state.state_version
                    seed = engine.rolling_seed()
                    if not getattr(seed, "seeded", False):
                        break  # nothing left to seed → target reached / done
                    store.save(engine.state, expected_version=before_seed_version)
            result = merged
        except LLMError as exc:
            error = str(exc)
            merged["error"] = error
            result = merged
        except (PipelineStateConflict, PipelineStateDigestError) as exc:
            error = f"Pipeline state conflict: {exc}"
            merged["error"] = error
            result = merged
        finally:
            # Persist whatever progress was made; release any task left
            # in-progress by an interrupted step (browser close, 502, etc.).
            self._finalize_pipeline_state(path, engine)

        if error:
            status_code = 409 if error.startswith("Pipeline state conflict:") else 502
            raise ServiceError(f"LLM run failed: {error}", status_code)
        return result

    def _run_step_locked(
        self,
        path: Path,
        *,
        db: Optional[Session] = None,
        user: Optional[User] = None,
    ) -> dict[str, Any]:
        """Run exactly ONE creative step (realtime driving for the web UI).

        Returns ``{step, finished, blocked, breaker_open, status}``. ``step`` is
        null when there is nothing left to do (seed exhausted → target reached).
        Each call performs at most one LLM generation, so the request stays
        short and the UI can stream progress by calling this in a loop.
        """
        if not self._dna_ready(path):
            raise ServiceError(
                "Chưa có PROJECT_DNA hợp lệ. Hãy tạo PROJECT_DNA (bước đầu tiên) "
                "trước khi sáng tác.",
                409,
            )
        from provider.llm_client import LLMClient, LLMError
        from provider import settings as ps

        config = (
            ps.load_config(db=db, user_id=user.id)
            if db is not None and user is not None
            else ps.load_config()
        )
        if not config.configured:
            raise ServiceError(
                "No LLM API key configured — open Settings and add your key.", 400
            )

        from integrations.autonovel.adapter import AutoNovelAdapter, AutoNovelWorkspace
        from integrations.autonovel.llm_loop import LLMAutoNovelLoop

        store = PipelineStateStore(path)
        state = self._load_state(path)
        engine = PipelineEngine(_state_from_dict(state))
        if self._release_stale_pipeline_claims(engine):
            store.save(engine.state, expected_version=state.get("state_version"))
        workspace = AutoNovelWorkspace(root=path)
        adapter = AutoNovelAdapter(
            engine,
            LLMAutoNovelLoop(client=LLMClient(config)),
            workspace,
            state_store=store,
        )

        if engine.state.breaker.is_open:
            return {"step": None, "finished": False, "blocked": True,
                    "breaker_open": True, "status": "blocked"}

        step: Optional[dict[str, Any]] = None
        error: Optional[str] = None
        try:
            step = adapter.step()
            if step is None:
                # Nothing ready — try to seed the next window, then retry once.
                before_seed_version = engine.state.state_version
                seed = engine.rolling_seed()
                if getattr(seed, "seeded", False):
                    store.save(engine.state, expected_version=before_seed_version)
                    step = adapter.step()
        except LLMError as exc:
            error = str(exc)
        except (PipelineStateConflict, PipelineStateDigestError) as exc:
            error = f"Pipeline state conflict: {exc}"
        finally:
            self._finalize_pipeline_state(path, engine)

        if error:
            status_code = 409 if error.startswith("Pipeline state conflict:") else 502
            raise ServiceError(f"LLM step failed: {error}", status_code)

        snapshot = self._status_snapshot(path) or {}
        return {
            "step": step,
            "finished": step is None,
            "blocked": engine.state.breaker.is_open,
            "breaker_open": engine.state.breaker.is_open,
            "status": snapshot.get("status"),
        }


def _state_from_dict(state: dict[str, Any]):
    """Rebuild a PipelineState from a serialised dict (import kept local)."""
    from tools.novelkit_pipeline_tool import PipelineState

    return PipelineState.from_dict(state)


# Module-level singleton used by the API routes.
SERVICE = NovelKitService()
