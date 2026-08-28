"""The per-novel run lock must never leak when acquiring it fails.

``_novel_run_lock`` takes an in-process ``threading.Lock`` and then opens the
cross-process ``logs/.run.lock`` file. If that second step raises — a full disk,
a read-only mount, a permission error — the thread lock has to come back, or the
novel is reported busy forever and the only cure is a process restart. The UI
maps that to ``alreadyRunning``, which it used to show as *nothing at all*, so
the symptom reached the user as "the next-step button does not work".

Symbols are looked up on the module on every call, never bound at import time:
other suites (``test_auth``, ``test_apple_auth``, ``test_dna_genre_e2e``) call
``importlib.reload`` on this module, which rebinds both ``RunBusyError`` and the
lock registry. A module-level ``from ... import RunBusyError`` would then hold a
stale class that no longer matches what the reloaded function raises.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import webapp.api.service as service


def test_lock_released_when_lock_file_cannot_be_opened(tmp_path, monkeypatch):
    """A failed ``open`` must not leave the novel permanently 'busy'."""
    real_open = open

    def _failing_open(file, *args, **kwargs):  # noqa: ANN001
        if str(file).endswith(".run.lock"):
            raise OSError(28, "No space left on device")
        return real_open(file, *args, **kwargs)

    monkeypatch.setattr("builtins.open", _failing_open)

    with pytest.raises(OSError):
        with service._novel_run_lock("leaky", tmp_path):
            pass

    # The real bug: this second attempt used to raise RunBusyError forever.
    monkeypatch.undo()
    with service._novel_run_lock("leaky", tmp_path):
        pass

    assert not service._novel_lock("leaky").locked()


def test_lock_released_when_lock_dir_cannot_be_created(tmp_path, monkeypatch):
    """Same guarantee when ``mkdir`` is what fails."""
    real_mkdir = Path.mkdir

    def _failing_mkdir(self, *args, **kwargs):  # noqa: ANN001
        if self.name == "logs":
            raise PermissionError(13, "Read-only file system")
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", _failing_mkdir)

    with pytest.raises(OSError):
        with service._novel_run_lock("readonly", tmp_path):
            pass

    monkeypatch.undo()
    with service._novel_run_lock("readonly", tmp_path):
        pass

    assert not service._novel_lock("readonly").locked()


def test_lock_released_when_body_raises(tmp_path):
    """An exception from the guarded block still releases both locks."""
    with pytest.raises(ValueError):
        with service._novel_run_lock("boom", tmp_path):
            raise ValueError("step failed")

    assert not service._novel_lock("boom").locked()
    with service._novel_run_lock("boom", tmp_path):
        pass


def test_contended_lock_still_reports_busy(tmp_path):
    """The fix must not weaken the actual busy signal."""
    with service._novel_run_lock("held", tmp_path):
        with pytest.raises(service.RunBusyError):
            with service._novel_run_lock("held", tmp_path):
                pass

    assert not service._novel_lock("held").locked()
