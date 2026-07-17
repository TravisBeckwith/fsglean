"""Tests for fsglean.parsers.wmparc."""

from pathlib import Path

import pandas as pd

from fsglean.parsers.wmparc import parse_wmparc

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseWmparc:

    def test_returns_dataframe(self):
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert isinstance(df, pd.DataFrame)

    def test_hemi_is_bilateral(self):
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert (df["hemi"] == "bilateral").all()

    def test_atlas_is_wmparc(self):
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert (df["atlas"] == "wmparc").all()

    def test_output_columns(self):
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert list(df.columns) == ["hemi", "atlas", "region", "metric", "value", "units"]

    def test_index_and_segid_excluded(self):
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert "Index" not in df["metric"].unique()
        assert "SegId" not in df["metric"].unique()

    def test_metrics_are_numeric(self):
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert pd.api.types.is_numeric_dtype(df["value"])

    def test_volume_units(self):
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert (df.loc[df["metric"] == "Volume_mm3", "units"] == "mm3").all()

    def test_correct_row_count(self):
        # 3 structures x 7 metrics = 21 rows
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert len(df) == 21

    def test_wm_structure_names_preserved(self):
        df = parse_wmparc(FIXTURES / "wmparc.stats")
        assert "wm-lh-bankssts" in df["region"].unique()
        assert "wm-rh-bankssts" in df["region"].unique()
