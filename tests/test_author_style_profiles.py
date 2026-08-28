"""Regression checks for neutral, identifier-only author profiles."""

from pathlib import Path


_AUTHOR_ROOT = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "novelkit-canon"
    / "canon"
    / "system"
)


def test_all_author_profiles_are_short_neutral_introductions():
    profiles = sorted(_AUTHOR_ROOT.glob("*/Author Style/*"))
    assert len(profiles) == 40

    for path in profiles:
        lines = path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 8, path
        assert lines[0].startswith("# "), path
        assert lines[2].startswith("- Mã tác giả: `") and lines[2].endswith("`"), path
        assert lines[3].startswith("- Nhóm tham chiếu: "), path
        assert lines[4] == "", path
        assert len(lines[5:]) == 3, path
        assert "chỉ cung cấp thông tin nhận diện khái quát" in lines[6], path
        assert "không chứa quy tắc hoặc chỉ dẫn nhằm mô phỏng" in lines[7], path

        lowered = "\n".join(lines).lower()
        for removed_marker in (
            "## ",
            "style rules",
            "system gate",
            "voice fingerprint",
            "mẫu câu",
            "cấm kỵ",
        ):
            assert removed_marker not in lowered, (path, removed_marker)
