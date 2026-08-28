from types import SimpleNamespace

import webapp.api.service as service_module
from webapp.api.service import NovelKitService


def test_manual_approval_marker_does_not_include_account_pii(tmp_path, monkeypatch):
    service = NovelKitService()
    monkeypatch.setattr(
        service,
        "_require_owned_novel",
        lambda db, user, name: (None, tmp_path),
    )
    monkeypatch.setattr(
        service,
        "_load_state",
        lambda path: {"state_version": 1},
    )
    monkeypatch.setattr(service, "_save_state", lambda *args, **kwargs: None)
    monkeypatch.setattr(service, "_refresh_snapshot", lambda *args: None)

    calls = []

    def fake_delegate(tool, **kwargs):
        calls.append((tool, kwargs))
        if tool == "novelkit_pipeline":
            return {"state": {"state_version": 2}, "result": {"ok": True}}
        return {"ok": True}

    monkeypatch.setattr(service_module, "delegate_tool", fake_delegate)
    user = SimpleNamespace(id="user-secret-id", email="author@example.com")

    service.approve_chapter(None, user, "privacy-test", chapter=1)

    sync_call = next(kwargs for tool, kwargs in calls if tool == "novelkit_sync")
    assert sync_call["approver"] == "local_operator"
    assert user.email not in repr(calls)
    assert user.id not in repr(calls)
