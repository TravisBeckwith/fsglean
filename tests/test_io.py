"""Tests for fsglean.io.find_sessions."""

from pathlib import Path

from fsglean.io import find_sessions


def _touch_stats_dir(base: Path) -> Path:
    d = base / "stats"
    d.mkdir(parents=True)
    return d


class TestFindSessions:

    def test_nested_layout(self, tmp_path):
        _touch_stats_dir(tmp_path / "sub-01" / "ses-V1")
        _touch_stats_dir(tmp_path / "sub-01" / "ses-V2")

        sessions = list(find_sessions(tmp_path))
        assert [(s.sub_id, s.ses_id) for s in sessions] == [
            ("sub-01", "ses-V1"),
            ("sub-01", "ses-V2"),
        ]

    def test_flat_layout(self, tmp_path):
        _touch_stats_dir(tmp_path / "sub-01_ses-V1")

        sessions = list(find_sessions(tmp_path))
        assert len(sessions) == 1
        assert sessions[0].sub_id == "sub-01"
        assert sessions[0].ses_id == "ses-V1"

    def test_cross_sectional_uses_fallback(self, tmp_path):
        _touch_stats_dir(tmp_path / "sub-01")

        sessions = list(find_sessions(tmp_path))
        assert len(sessions) == 1
        assert sessions[0].ses_id == "ses-01"

    def test_cross_sectional_custom_fallback(self, tmp_path):
        _touch_stats_dir(tmp_path / "sub-01")

        sessions = list(find_sessions(tmp_path, fallback_ses_id="ses-baseline"))
        assert sessions[0].ses_id == "ses-baseline"

    def test_cross_sectional_no_fallback_is_none(self, tmp_path):
        _touch_stats_dir(tmp_path / "sub-01")

        sessions = list(find_sessions(tmp_path, fallback_ses_id=None))
        assert sessions[0].ses_id is None

    def test_subject_without_stats_dir_skipped(self, tmp_path):
        (tmp_path / "sub-01").mkdir()  # no stats/ subdir at all

        sessions = list(find_sessions(tmp_path))
        assert sessions == []

    def test_session_without_stats_dir_skipped(self, tmp_path):
        (tmp_path / "sub-01" / "ses-V1").mkdir(parents=True)  # no stats/
        _touch_stats_dir(tmp_path / "sub-01" / "ses-V2")

        sessions = list(find_sessions(tmp_path))
        assert len(sessions) == 1
        assert sessions[0].ses_id == "ses-V2"

    def test_non_subject_directories_ignored(self, tmp_path):
        (tmp_path / "derivatives").mkdir()
        (tmp_path / "code").mkdir()
        _touch_stats_dir(tmp_path / "sub-01")

        sessions = list(find_sessions(tmp_path))
        assert len(sessions) == 1

    def test_sorted_output(self, tmp_path):
        _touch_stats_dir(tmp_path / "sub-02")
        _touch_stats_dir(tmp_path / "sub-01")

        sessions = list(find_sessions(tmp_path))
        assert [s.sub_id for s in sessions] == ["sub-01", "sub-02"]

    def test_stats_file_helper(self, tmp_path):
        stats_dir = _touch_stats_dir(tmp_path / "sub-01")
        (stats_dir / "aseg.stats").write_text("dummy")

        sessions = list(find_sessions(tmp_path))
        session = sessions[0]
        assert session.stats_file("aseg.stats") == stats_dir / "aseg.stats"
        assert session.stats_file("does_not_exist.stats") is None
