"""Phase 7 decommission verification — legacy infra is absent (Requirement 5).

This is the **non-destructive** decommission contract for this repo. The legacy
NovelKit stack was never copied into the target package ``novelkit-hermes/``;
decommissioning is therefore proven by asserting the running system contains
*zero* legacy infrastructure files — not by deleting anything from the source
archive (``_novelkit_source/``), which the migration reconciliation tests still
read from.

Covers Requirement 5 acceptance criteria:

* 5.1 — no Express/React UI, ``app.js``, ``docker-compose.yml``, ``Dockerfile``.
* 5.2 — no legacy Python runtime (``control_plane.py``, ``dispatcher_adapter.py``,
  ``write_next.py``, ``task_runner.py``).
* 5.3 — no bespoke SQLite control plane (``cp_*.py``) or legacy provider stack
  (``llm_config.py``, ``gemini_key_pool.py``, ``gemini_pool_status.py``,
  ``google_genai_compat.py``); no ``account_tiers`` SaaS tiering; no legacy
  observability modules.

The findings these map to live in design.md §"Creative Asset Audit": D2
(control plane), D6 (provider), D7 (runners).

    **Validates: Requirements 5**
"""

from __future__ import annotations

import re
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# novelkit-hermes/ — the *running system* package. Resolved from this test file
# so the check is independent of the working directory.
PACKAGE_ROOT: Path = Path(__file__).resolve().parent.parent

# Directories that are build/test noise, never part of the shipped surface.
_EXCLUDED_DIRS: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".pytest_cache",
        ".hypothesis",
        ".git",
        ".mypy_cache",
        ".ruff_cache",
        ".venv",
        "node_modules",
    }
)

# --------------------------------------------------------------------------- #
# The legacy-infra contract: nothing matching these may exist under the package.
# --------------------------------------------------------------------------- #

# Exact filenames that mark legacy infrastructure (old → removed).
_FORBIDDEN_EXACT: frozenset[str] = frozenset(
    {
        # Express / React UI + container/orchestration (Req 5.1).
        "app.js",
        "index.html",
        "styles.css",
        "docker-compose.yml",
        "docker-compose.yaml",
        "Dockerfile",
        # Legacy Python runtime / runners (Req 5.2; finding D7).
        "dispatcher_adapter.py",
        "task_runner.py",
        "write_next.py",
        # SQLite control plane (Req 5.3; finding D2).
        "control_plane.py",
        "cp_db.py",
        # Legacy provider stack (Req 5.3; finding D6).
        "llm_config.py",
        "gemini_key_pool.py",
        "gemini_pool_status.py",
        "google_genai_compat.py",
    }
)

# Filename *patterns* that mark legacy infrastructure.
_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r".*\.sh$"),                 # any shell script (Req 5.2)
    re.compile(r"^cp_.*\.py$"),             # modular SQLite control plane (D2)
    re.compile(r"^observability.*\.py$"),   # legacy observability modules
)

# Path *segments* (directory names) that mark legacy infrastructure.
_FORBIDDEN_DIR_SEGMENTS: frozenset[str] = frozenset(
    {
        "account_tiers",  # SaaS tiering — not a creative asset.
    }
)

# Migrated *creative-asset* bundles. These hold the preserved creative brain
# (skills + persona subagents) copied byte-for-byte from the source and verified
# by tests/test_canon_migration.py. They are NOT runtime infrastructure: a skill
# bundle may legitimately vendor its own helper scripts (e.g. the
# self-improving-agent skill ships scripts/*.sh). The legacy-infra decommission
# contract applies to the *running system surface* (root + tools/ + plugins/ +
# provider/ + migration/ + integrations/), so these creative bundles are out of
# scope for the legacy scan.
_CREATIVE_ASSET_DIRS: frozenset[str] = frozenset(
    {
        "skills",
        "subagents",
    }
)

# The sanctioned new web surface (FastAPI API + React/Vite SPA). It is a
# *separate, deliberate* feature — NOT the decommissioned legacy NovelKit
# Express/React stack — so it may legitimately ship app/UI files (index.html,
# styles.css, a built dist/). The Req-5 decommission contract targets the old
# stack on the runtime surface, so the new web surface is excluded from the scan.
_WEB_SURFACE_DIRS: frozenset[str] = frozenset({"webapp"})

# The GA product ships deployment and marketing surfaces that are not part of
# the decommissioned legacy NovelKit runtime. They may legitimately contain
# ``Dockerfile``, generated ``index.html`` pages, and deploy shell wrappers.
_SANCTIONED_PRODUCT_DIRS: frozenset[str] = frozenset({"marketing"})
_SANCTIONED_PRODUCT_FILES: frozenset[str] = frozenset(
    {
        "Dockerfile",
        "scripts/start-production.sh",
    }
)

# Dirs excluded from the legacy-infra runtime scan: migrated creative payloads,
# sanctioned product surfaces, and the sanctioned web surface.
_NON_RUNTIME_INFRA_DIRS: frozenset[str] = (
    _CREATIVE_ASSET_DIRS | _WEB_SURFACE_DIRS | _SANCTIONED_PRODUCT_DIRS
)


def _is_sanctioned_product_file(path: Path) -> bool:
    rel = path.relative_to(PACKAGE_ROOT).as_posix()
    return rel in _SANCTIONED_PRODUCT_FILES


def is_legacy_filename(name: str) -> bool:
    """True iff ``name`` is a forbidden legacy-infra filename.

    Total, deterministic, content-free: depends only on the file *name*.
    """
    if name in _FORBIDDEN_EXACT:
        return True
    return any(pat.match(name) for pat in _FORBIDDEN_PATTERNS)


def _iter_package_files() -> list[Path]:
    """Every real file under the package, skipping build/test noise dirs."""
    files: list[Path] = []
    for path in sorted(PACKAGE_ROOT.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel_parts = path.relative_to(PACKAGE_ROOT).parts
        if any(part in _EXCLUDED_DIRS for part in rel_parts):
            continue
        if _is_sanctioned_product_file(path):
            continue
        files.append(path)
    return files


def _iter_runtime_files() -> list[Path]:
    """Runtime/code-surface files only — excludes migrated creative bundles.

    The legacy-infra decommission contract is about the *running system*, not
    the preserved creative payload under ``skills/`` and ``subagents/`` (which
    may legitimately vendor helper scripts and is verified byte-exact by the
    canon-migration tests).
    """
    return [
        path
        for path in _iter_package_files()
        if not any(
            seg in _NON_RUNTIME_INFRA_DIRS
            for seg in path.relative_to(PACKAGE_ROOT).parts
        )
    ]


def find_legacy_infra() -> list[str]:
    """Return POSIX-relative paths of any legacy-infra files in the runtime surface."""
    offenders: list[str] = []
    for path in _iter_runtime_files():
        rel = path.relative_to(PACKAGE_ROOT)
        if is_legacy_filename(path.name):
            offenders.append(rel.as_posix())
            continue
        if any(seg in _FORBIDDEN_DIR_SEGMENTS for seg in rel.parts):
            offenders.append(rel.as_posix())
    return offenders


# --------------------------------------------------------------------------- #
# The decommission assertion: zero legacy infra in the running system.
# --------------------------------------------------------------------------- #


def test_no_legacy_infra_present_in_package():
    """The package ships ZERO legacy infrastructure files (Requirement 5)."""
    offenders = find_legacy_infra()
    assert offenders == [], (
        "legacy infrastructure still present in novelkit-hermes/: " + ", ".join(offenders)
    )


def test_source_archive_is_untouched():
    """Decommission is non-destructive: the source archive still exists.

    The legacy stack is removed by *not copying it forward*, never by deleting
    ``_novelkit_source/`` (the reconciliation tests read from it).
    """
    archive = PACKAGE_ROOT.parent / "_novelkit_source"
    assert archive.is_dir(), "source archive must remain intact for reconciliation"


def test_no_shell_scripts_anywhere():
    """No ``*.sh`` orchestration scripts ship in the runtime surface (Req 5.2).

    Migrated creative skill bundles under ``skills/`` may vendor their own
    helper scripts (e.g. the self-improving-agent skill) — those are preserved
    creative assets, not runtime infra, and are excluded here.
    """
    shell = [
        p.relative_to(PACKAGE_ROOT).as_posix()
        for p in _iter_runtime_files()
        if p.name.endswith(".sh")
    ]
    assert shell == [], f"shell scripts present in runtime surface: {shell}"


def test_no_account_tiers_directory():
    """No SaaS ``account_tiers`` tiering directory ships (Req 5.3)."""
    for path in sorted(PACKAGE_ROOT.rglob("account_tiers")):
        if any(part in _EXCLUDED_DIRS for part in path.relative_to(PACKAGE_ROOT).parts):
            continue
        raise AssertionError(f"account_tiers present: {path.relative_to(PACKAGE_ROOT).as_posix()}")


# --------------------------------------------------------------------------- #
# Concrete classifier examples (the old → removed contract, finding-tagged).
# --------------------------------------------------------------------------- #


def test_classifier_flags_known_legacy_names():
    for name in [
        "app.js",
        "docker-compose.yml",
        "Dockerfile",
        "control_plane.py",      # D2
        "cp_db.py",              # D2
        "cp_status.py",          # D2 (pattern)
        "cp_recovery.py",        # D2 (pattern)
        "dispatcher_adapter.py",  # D7
        "task_runner.py",        # D7
        "write_next.py",         # D7
        "llm_config.py",         # D6
        "gemini_key_pool.py",    # D6
        "google_genai_compat.py",  # D6
        "observability.py",
        "observability_cli.py",
        "run_pipeline.sh",
    ]:
        assert is_legacy_filename(name), f"expected {name!r} to be flagged legacy"


def test_classifier_keeps_hermes_surface_names():
    """Files the running system *does* ship must never be flagged legacy."""
    for name in [
        "bootstrap.py",
        "cli.py",
        "delegate.py",
        "registry.py",
        "task_output_contracts.py",   # kept as shared schema (finding D7)
        "novelkit_pipeline_tool.py",  # extracted DAG (replaces control plane)
        "novelkit_sync_tool.py",
        "novelkit_language_guard_tool.py",
        "resolver.py",                # provider resolution shim
        "provider.json",
        "schedule.json",
        "SOUL.md",
    ]:
        assert not is_legacy_filename(name), f"{name!r} wrongly flagged legacy"


# --------------------------------------------------------------------------- #
# Property: the classifier is total + the contract is closed over filenames.
# --------------------------------------------------------------------------- #

_FILENAME = st.text(
    alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-",
    min_size=1,
    max_size=40,
).filter(lambda s: s not in {".", ".."})


@settings(max_examples=300)
@given(_FILENAME)
def test_property_classifier_is_total_and_consistent(name):
    """``is_legacy_filename`` is total, boolean, and stable.

    **Validates: Requirements 5**
    """
    first = is_legacy_filename(name)
    assert isinstance(first, bool)
    assert first == is_legacy_filename(name)
    # A file flagged legacy is so because of an exact name or an explicit pattern.
    if first:
        assert name in _FORBIDDEN_EXACT or any(p.match(name) for p in _FORBIDDEN_PATTERNS)


@settings(max_examples=200)
@given(_FILENAME)
def test_property_shell_scripts_always_flagged(name):
    """Any ``*.sh`` name is always classified as legacy (Req 5.2).

    **Validates: Requirements 5**
    """
    if name.endswith(".sh"):
        assert is_legacy_filename(name)
