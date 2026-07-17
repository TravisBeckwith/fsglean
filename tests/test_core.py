"""Tests for fsglean.core.FSGlean."""

from pathlib import Path

import pandas as pd
import pytest

from fsglean import FSGlean

FIXTURES = Path(__file__).parent / "fixtures"


def _write_tree(root: Path, layout: dict):
    """layout: {sub_dir_name: {stats_filename: fixture_name_or_text}}"""
    fixture_cache = {}

    def _content(name):
        if name not in fixture_cache:
            fixture_cache[name] = (FIXTURES / name).read_text()
        return fixture_cache[name]

    for sub_dir_name, files in layout.items():
        stats_dir = root / sub_dir_name / "stats"
        stats_dir.mkdir(parents=True)
        for filename, fixture_name in files.items():
            (stats_dir / filename).write_text(_content(fixture_name))


@pytest.fixture
def simple_tree(tmp_path):
    """sub-01/sub-02, both cross-sectional, full aparc + aseg data."""
    _write_tree(
        tmp_path,
        {
            "sub-01": {
                "lh.aparc.stats": "lh.aparc.stats",
                "rh.aparc.stats": "lh.aparc.stats",
                "aseg.stats": "aseg.stats",
            },
            "sub-02": {
                "lh.aparc.stats": "lh.aparc.stats",
                "rh.aparc.stats": "lh.aparc.stats",
                "aseg.stats": "aseg.stats",
            },
        },
    )
    return tmp_path


@pytest.fixture
def tree_with_missing_file(tmp_path):
    """sub-01 has everything; sub-02 is missing aseg.stats."""
    _write_tree(
        tmp_path,
        {
            "sub-01": {
                "lh.aparc.stats": "lh.aparc.stats",
                "rh.aparc.stats": "lh.aparc.stats",
                "aseg.stats": "aseg.stats",
            },
            "sub-02": {
                "lh.aparc.stats": "lh.aparc.stats",
                "rh.aparc.stats": "lh.aparc.stats",
            },
        },
    )
    return tmp_path


class TestConstruction:

    def test_unknown_stats_choice_raises(self, simple_tree):
        with pytest.raises(ValueError, match="Unknown --stats"):
            FSGlean(simple_tree, stats=["not_a_real_stat"])

    def test_nonexistent_dir_raises(self, tmp_path):
        with pytest.raises(ValueError, match="does not exist"):
            FSGlean(tmp_path / "nope")


class TestToLong:

    def test_returns_dataframe_with_sub_ses_columns(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc", "aseg"])
        df = ext.to_long()
        assert isinstance(df, pd.DataFrame)
        assert {"sub_id", "ses_id", "hemi", "atlas", "region", "metric", "value", "units"} <= set(df.columns)

    def test_includes_all_requested_subjects(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"])
        df = ext.to_long()
        assert set(df["sub_id"].unique()) == {"sub-01", "sub-02"}

    def test_cortical_kind_filter(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc", "aseg"])
        df = ext.to_long(kind="cortical")
        assert set(df["atlas"].unique()) == {"desikan-killiany"}

    def test_subcortical_kind_filter(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc", "aseg"])
        df = ext.to_long(kind="subcortical")
        assert set(df["atlas"].unique()) == {"aseg"}

    def test_invalid_kind_raises(self, simple_tree):
        ext = FSGlean(simple_tree)
        with pytest.raises(ValueError, match="kind must be"):
            ext.to_long(kind="not_a_kind")

    def test_metrics_filter(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"], metrics=["ThickAvg"])
        df = ext.to_long()
        assert set(df["metric"].unique()) == {"ThickAvg"}

    def test_subjects_filter(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"], subjects=["sub-01"])
        df = ext.to_long()
        assert set(df["sub_id"].unique()) == {"sub-01"}

    def test_empty_tree_returns_empty_frame(self, tmp_path):
        ext = FSGlean(tmp_path, stats=["aparc"])
        df = ext.to_long()
        assert df.empty


class TestToWide:

    def test_one_row_per_sub(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc", "aseg"])
        wide = ext.to_wide()
        assert len(wide) == 2
        assert set(wide["sub_id"]) == {"sub-01", "sub-02"}

    def test_cortical_column_naming(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"])
        wide = ext.to_wide()
        assert "lh_bankssts_ThickAvg" in wide.columns

    def test_subcortical_column_naming_sanitizes_hyphens(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aseg"])
        wide = ext.to_wide()
        assert "Left_Hippocampus_Volume_mm3" in wide.columns
        assert not any("-" in c for c in wide.columns)

    def test_missing_file_becomes_nan(self, tree_with_missing_file):
        ext = FSGlean(tree_with_missing_file, stats=["aparc", "aseg"])
        wide = ext.to_wide()
        row = wide[wide["sub_id"] == "sub-02"].iloc[0]
        assert pd.isna(row["Left_Hippocampus_Volume_mm3"])

    def test_dk_dkt_collision_raises(self, tmp_path):
        # DK and DKTatlas share many region names (e.g. bankssts) — this is
        # a realistic collision, not a contrived one.
        _write_tree(
            tmp_path,
            {
                "sub-01": {
                    "lh.aparc.stats": "lh.aparc.stats",
                    "rh.aparc.stats": "lh.aparc.stats",
                    "lh.aparc.DKTatlas.stats": "lh.aparc.stats",
                    "rh.aparc.DKTatlas.stats": "lh.aparc.stats",
                },
            },
        )
        ext = FSGlean(tmp_path, stats=["aparc", "aparc.DKTatlas"])
        with pytest.raises(ValueError, match="collision"):
            ext.to_wide()


class TestDataDictionary:

    def test_one_row_per_wide_column(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc", "aseg"])
        dd = ext.data_dictionary()
        wide_cols = set(ext.to_wide().columns) - {"sub_id", "ses_id"}
        assert set(dd["column_name"]) == wide_cols

    def test_expected_columns_present(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"])
        dd = ext.data_dictionary()
        assert list(dd.columns) == [
            "column_name",
            "description",
            "units",
            "atlas",
            "source_file",
            "freesurfer_metric",
        ]

    def test_source_file_correct(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"])
        dd = ext.data_dictionary()
        lh_rows = dd[dd["column_name"].str.startswith("lh_")]
        assert (lh_rows["source_file"] == "lh.aparc.stats").all()


class TestManifest:

    def test_one_row_per_sub_ses(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"])
        m = ext.manifest()
        assert len(m) == 2

    def test_missing_file_tracked(self, tree_with_missing_file):
        ext = FSGlean(tree_with_missing_file, stats=["aparc", "aseg"])
        m = ext.manifest()
        row = m[m["sub_id"] == "sub-02"].iloc[0]
        assert not row["aseg_found"]
        assert "aseg.stats missing" in row["notes"]

    def test_found_flags_true_when_present(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc", "aseg"])
        m = ext.manifest()
        assert m["lh_aparc_found"].all()
        assert m["rh_aparc_found"].all()
        assert m["aseg_found"].all()

    def test_qc_threshold_zero_disables_flagging(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"], qc_threshold=0)
        m = ext.manifest()
        assert not m["qc_flag"].any()


class TestSessionFallback:

    def test_default_fallback(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"])
        m = ext.manifest()
        assert (m["ses_id"] == "ses-01").all()

    def test_no_fallback_leaves_none(self, simple_tree):
        ext = FSGlean(simple_tree, stats=["aparc"], session_fallback=None)
        m = ext.manifest()
        assert m["ses_id"].isna().all()
