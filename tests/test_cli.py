"""Tests for fsglean.cli."""

from pathlib import Path

from click.testing import CliRunner

from fsglean.cli import main

FIXTURES = Path(__file__).parent / "fixtures"


def _write_synthetic_tree(root: Path):
    lh_aparc = (FIXTURES / "lh.aparc.stats").read_text()
    aseg = (FIXTURES / "aseg.stats").read_text()

    for sub in ("sub-01", "sub-02"):
        d = root / sub / "stats"
        d.mkdir(parents=True)
        (d / "lh.aparc.stats").write_text(lh_aparc)
        (d / "rh.aparc.stats").write_text(lh_aparc)
        (d / "aseg.stats").write_text(aseg)


class TestCLI:

    def test_help(self):
        result = CliRunner().invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "DERIVATIVES_DIR" in result.output

    def test_nonexistent_dir_errors_cleanly(self):
        result = CliRunner().invoke(main, ["/no/such/path"])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_default_run_writes_five_files(self, tmp_path):
        _write_synthetic_tree(tmp_path / "derivatives")
        output = tmp_path / "out"

        result = CliRunner().invoke(
            main, [str(tmp_path / "derivatives"), "--output", str(output)]
        )
        assert result.exit_code == 0, result.output
        expected = {
            "cortical_long.csv",
            "subcortical_long.csv",
            "merged_wide.csv",
            "data_dictionary.csv",
            "manifest.csv",
        }
        assert expected <= {p.name for p in output.iterdir()}

    def test_no_dict_no_manifest(self, tmp_path):
        _write_synthetic_tree(tmp_path / "derivatives")
        output = tmp_path / "out"

        result = CliRunner().invoke(
            main,
            [
                str(tmp_path / "derivatives"),
                "--output",
                str(output),
                "--no-dict",
                "--no-manifest",
            ],
        )
        assert result.exit_code == 0, result.output
        names = {p.name for p in output.iterdir()}
        assert "data_dictionary.csv" not in names
        assert "manifest.csv" not in names

    def test_format_long_only(self, tmp_path):
        _write_synthetic_tree(tmp_path / "derivatives")
        output = tmp_path / "out"

        result = CliRunner().invoke(
            main, [str(tmp_path / "derivatives"), "--output", str(output), "--format", "long"]
        )
        assert result.exit_code == 0, result.output
        names = {p.name for p in output.iterdir()}
        assert "merged_wide.csv" not in names
        assert "cortical_long.csv" in names

    def test_empty_derivatives_dir_no_crash(self, tmp_path):
        empty = tmp_path / "empty"
        empty.mkdir()
        output = tmp_path / "out"

        result = CliRunner().invoke(main, [str(empty), "--output", str(output)])
        assert result.exit_code == 0
        assert "No subjects found" in result.output
        assert not output.exists()

    def test_unknown_stats_choice_rejected_by_click(self, tmp_path):
        _write_synthetic_tree(tmp_path / "derivatives")
        result = CliRunner().invoke(
            main, [str(tmp_path / "derivatives"), "--stats", "not_a_real_stat"]
        )
        assert result.exit_code != 0

    def test_stats_repeated_flag_syntax(self, tmp_path):
        _write_synthetic_tree(tmp_path / "derivatives")
        output = tmp_path / "out"
        result = CliRunner().invoke(
            main,
            [
                str(tmp_path / "derivatives"),
                "--stats",
                "aparc",
                "--stats",
                "aseg",
                "--output",
                str(output),
            ],
        )
        assert result.exit_code == 0, result.output
