from __future__ import annotations

import json
import tempfile
from pathlib import Path

from tools.novelkit_diagnostics_tool import export_diagnostics


def test_diagnostics_export_redacts_prose_prompt_credentials_and_rule_text():
    novel = Path(tempfile.mkdtemp()) / "diagnostics-demo"
    (novel / "chapters").mkdir(parents=True)
    (novel / "reviews").mkdir()
    (novel / "logs").mkdir()
    (novel / "chapters" / "chapter_001.md").write_text(
        "SECRET_PROSE_SHOULD_NOT_LEAK", encoding="utf-8"
    )
    (novel / "PROJECT_DNA.rules.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "revision": 1,
                "rules": [
                    {
                        "rule_id": "user_0001",
                        "scope": "style",
                        "kind": "preference",
                        "text": "PRIVATE_RULE_TEXT_SHOULD_NOT_LEAK",
                        "normalized": {"target": "style", "operator": "prefer"},
                        "enforcement": "preference",
                        "source": "runtime_user_update",
                        "created_at": "2026-06-29T00:00:00Z",
                    }
                ],
                "updated_at": "2026-06-29T00:00:00Z",
            }
        ),
        encoding="utf-8",
    )
    (novel / "logs" / "provider.log").write_text(
        "raw_prompt=RAW_PROMPT_SHOULD_NOT_LEAK api_key=sk-SECRET",
        encoding="utf-8",
    )
    (novel / "reviews" / "chapter_0001_review.json").write_text(
        json.dumps(
            {
                "schema_version": 2,
                "review_id": "chapter_0001_attempt_01",
                "chapter": 1,
                "overall_score": 86,
                "gate_outcome": "pass",
                "issues": [
                    {
                        "code": "dialogue_flat",
                        "severity": "warning",
                        "excerpt": "SECRET_EXCERPT_SHOULD_NOT_LEAK",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exported = export_diagnostics(novel)
    serialized = json.dumps(exported, ensure_ascii=False)

    assert "SECRET_PROSE_SHOULD_NOT_LEAK" not in serialized
    assert "PRIVATE_RULE_TEXT_SHOULD_NOT_LEAK" not in serialized
    assert "RAW_PROMPT_SHOULD_NOT_LEAK" not in serialized
    assert "sk-SECRET" not in serialized
    assert "SECRET_EXCERPT_SHOULD_NOT_LEAK" not in serialized
    assert exported["runtime"]["artifact_manifest"]
    assert exported["creative"]["review_trend"] == [
        {
            "chapter": 1,
            "review_id": "chapter_0001_attempt_01",
            "overall_score": 86,
            "gate_outcome": "pass",
            "issue_codes": ["dialogue_flat"],
        }
    ]
