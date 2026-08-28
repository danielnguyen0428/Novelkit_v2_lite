"""Acceptance tests for the local-only Lite surface."""

from __future__ import annotations

import importlib

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("NOVELKIT_WORKSPACE_ROOT", str(tmp_path / "workspaces"))
    monkeypatch.setenv("NOVELKIT_STORAGE_ROOT", str(tmp_path / "storage"))
    monkeypatch.setenv("NOVELKIT_SECRETS_DIR", str(tmp_path / ".secrets"))

    import webapp.api.novel_paths as novel_paths
    import webapp.api.service as service

    importlib.reload(novel_paths)
    importlib.reload(service)

    import webapp.api.main as main

    importlib.reload(main)
    with TestClient(main.app) as test_client:
        yield test_client


def test_lite_health_and_studio(client: TestClient) -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert health.json()["tools"] >= 10
    assert (
        health.headers["X-NovelKit-Provenance"]
        == "NOVELKIT-V2-LITE-DN0428-20260828-12A133B9E572"
    )

    provenance = client.get("/api/provenance")
    assert provenance.status_code == 200
    assert provenance.json()["canonical_repository"] == (
        "https://github.com/danielnguyen0428/Novelkit_v2_lite"
    )
    assert provenance.json()["origin_commit"] == (
        "12a133b9e5729ac221c014a2ec14cb6af251fef4"
    )
    assert provenance.json()["telemetry"] is False

    studio = client.get("/")
    assert studio.status_code == 200


@pytest.mark.parametrize(
    "path",
    [
        "/api/me",
        "/api/auth/google",
        "/api/billing/plans",
        "/api/account/history",
        "/api/public/catalog",
    ],
)
def test_online_account_and_commerce_routes_are_absent(
    client: TestClient, path: str
) -> None:
    assert client.get(path).status_code == 404


def test_provider_settings_are_custom_only_and_secret_free(client: TestClient) -> None:
    initial = client.get("/api/settings")
    assert initial.status_code == 200
    assert initial.json()["mode"] == "custom"
    assert "credit_balance" not in initial.json()

    saved = client.put(
        "/api/settings",
        json={
            "provider": "other",
            "base_url": "https://api.openai.com/v1",
            "model": "gpt-4o-mini",
            "api_key": "sk-lite-acceptance-test",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["mode"] == "custom"
    assert saved.json()["api_key_set"] is True
    assert "sk-lite-acceptance-test" not in saved.text


def test_local_novel_lifecycle(client: TestClient) -> None:
    created = client.post(
        "/api/novels",
        json={
            "name": "lite_demo",
            "fields": {
                "title": "Lite Demo",
                "genre": "xianxia",
                "logline": "Một người viết thử bản local độc lập.",
                "target_chapters": 2,
            },
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "lite_demo"

    listing = client.get("/api/novels")
    assert listing.status_code == 200
    assert [item["name"] for item in listing.json()] == ["lite_demo"]
