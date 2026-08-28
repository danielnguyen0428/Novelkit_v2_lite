"""Minor-cast roster memory category (Req 6; Property P18)."""

from __future__ import annotations

from plugins.memory.novelkit_memory import (
    Category,
    get_provider,
    recent_cast,
)


def _commit(provider, scope, chapter, payload, value="chủ quán"):
    provider.commit_episodic(
        scope=scope,
        memory_facts=[
            {
                "category": "minor_cast",
                "subject": "Lão Chu",
                "field": "profile",
                "value": value,
                "payload": payload,
            }
        ],
        chapter=chapter,
        commit_id=f"c{chapter}",
    )


def test_minor_cast_monotonic_merge(tmp_path):
    p = get_provider()
    _commit(p, tmp_path, 7, {"brief_role": "chủ quán", "first_seen": 7,
                             "last_seen": 7, "appearance_count": 1})
    _commit(p, tmp_path, 42, {"last_seen": 42, "appearance_count": 4})
    items = [i for i in recent_cast(tmp_path) if i.subject == "Lão Chu"]
    assert len(items) == 1  # deduped by name (P18)
    it = items[0]
    assert it.payload["appearance_count"] >= 4
    assert it.payload["last_seen"] == 42
    assert it.payload["first_seen"] == 7
    assert it.payload["last_seen"] >= it.payload["first_seen"]


def test_minor_cast_idempotent_when_unchanged(tmp_path):
    p = get_provider()
    payload = {"brief_role": "chủ quán", "first_seen": 7, "last_seen": 7,
               "appearance_count": 1}
    _commit(p, tmp_path, 7, payload)
    before = recent_cast(tmp_path)[0].updated_at
    _commit(p, tmp_path, 7, payload)  # identical
    after = recent_cast(tmp_path)[0].updated_at
    assert before == after  # no churn


def test_recent_cast_ordered_and_limited(tmp_path):
    p = get_provider()
    for i, name in enumerate(["A", "B", "C"], start=1):
        p.commit_episodic(
            scope=tmp_path,
            memory_facts=[{"category": "minor_cast", "subject": name,
                           "field": "profile", "value": "npc",
                           "payload": {"first_seen": i, "last_seen": i * 10,
                                       "appearance_count": 1}}],
            chapter=i, commit_id=f"c{i}",
        )
    names = [i.subject for i in recent_cast(tmp_path, limit=2)]
    assert names == ["C", "B"]  # newest last_seen first, limited to 2


def test_minor_cast_category_enum():
    assert Category.MINOR_CAST.value == "minor_cast"


def test_minor_cast_isolated_per_novel(tmp_path):
    p = get_provider()
    a, b = tmp_path / "novelA", tmp_path / "novelB"
    a.mkdir(); b.mkdir()
    _commit(p, a, 1, {"first_seen": 1, "last_seen": 1, "appearance_count": 1})
    assert any(i.subject == "Lão Chu" for i in recent_cast(a))
    assert recent_cast(b) == []  # per-novel isolation (P7)


def test_tentative_minor_cast_promoted_to_active_on_merge(tmp_path):
    """A tentative roster entry must become active when a later merge touches it;
    otherwise it stays tentative forever and never surfaces via recent_cast."""
    from plugins.memory.novelkit_memory import Status

    p = get_provider()
    store = p.store(tmp_path)
    # Seed a TENTATIVE roster entry directly.
    store.upsert_many([
        _coerce_tentative("Lão Chu", chapter=7,
                          payload={"brief_role": "chủ quán", "first_seen": 7,
                                   "last_seen": 7, "appearance_count": 1}),
    ])
    # Before the fix, recent_cast (status=active only) would not see it.
    assert recent_cast(tmp_path) == []
    # A subsequent minor_cast commit for the same name must promote it to active.
    _commit(p, tmp_path, 20, {"last_seen": 20, "appearance_count": 2})
    surfaced = [i for i in recent_cast(tmp_path) if i.subject == "Lão Chu"]
    assert len(surfaced) == 1
    assert surfaced[0].status == Status.ACTIVE


def _coerce_tentative(subject, *, chapter, payload):
    from plugins.memory.novelkit_memory import Category, MemoryItem, Status

    return MemoryItem(
        id=f"tent_{subject}",
        category=Category.MINOR_CAST,
        subject=subject,
        field="profile",
        value=payload.get("brief_role") or subject,
        payload=payload,
        status=Status.TENTATIVE,
        source_chapter=chapter,
        source_commit_id=f"c{chapter}",
    )
