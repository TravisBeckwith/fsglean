"""Tests for fsglean.parsers.aparc and fsglean.parsers.aseg."""

import pandas as pd
import pytest
from pathlib import Path

from fsglean.parsers.aparc import parse_aparc
from fsglean.parsers.aseg import parse_aseg

FIXTURES = Path(__file__).parent / "fixtures"

# ---------------------------------------------------------------------------
# aparc.stats tests
# ---------------------------------------------------------------------------

class TestParseAparc:

    def test_returns_dataframe(self):
        df = parse_aparc(FIXTURES / "lh.aparc.stats")
        assert isinstance(df, pd.DataFrame)

    def test_hemi_inferred_lh(self):
        df = parse_aparc(FIXTURES / "lh.aparc.stats")
        assert (df["hemi"] == "lh").all()

    def test_hemi_inferred_rh(self, tmp_path):
        src = FIXTURES / "lh.aparc.stats"
        dst = tmp_path / "rh.aparc.stats"
        dst.write_text(src.read_text())
        df = parse_aparc(dst)
        assert (df["hemi"] == "rh").all()

    def test_hemi_explicit_overrides_filename(self, tmp_path):
        src = FIXTURES / "lh.aparc.stats"
        dst = tmp_path / "lh.aparc.stats"
        dst.write_text(src.read_text())
        df = parse_aparc(dst, hemi="rh")
        assert (df["hemi"] == "rh").all()

    def test_atlas_desikan_killiany(self):
        df = parse_aparc(FIXTURES / "lh.aparc.stats")
        assert (df["atlas"] == "desikan-killiany").all()

    def test_output_columns(self):
        df = parse_aparc(FIXTURES / "lh.aparc.stats")
        assert list(df.columns) == ["hemi", "atlas", "region", "metric", "value", "units"]

    def test_metrics_are_numeric(self):
        df = parse_aparc(FIXTURES / "lh.aparc.stats")
        assert pd.api.types.is_numeric_dtype(df["value"])

    def test_thickavg_units(self):
        df = parse_aparc(FIXTURES / "lh.aparc.stats")
        assert (df.loc[df["metric"] == "ThickAvg", "units"] == "mm").all()

    def test_surfarea_units(self):
        df = parse_aparc(FIXTURES / "lh.aparc.stats")
        assert (df.loc[df["metric"] == "SurfArea", "units"] == "mm2").all()

    def test_correct_row_count(self):
        # 3 regions x 9 metrics = 27 rows
        df = parse_aparc(FIXTURES / "lh.aparc.stats")
        assert len(df) == 27

    def test_missing_colheaders_raises(self, tmp_path):
        bad = tmp_path / "lh.aparc.stats"
        bad.write_text("# some comment\nbankssts 1 2 3 4 5 6 7 8 9\n")
        with pytest.raises(ValueError, match="ColHeaders"):
            parse_aparc(bad)

    def test_unknown_hemi_raises(self, tmp_path):
        src = FIXTURES / "lh.aparc.stats"
        dst = tmp_path / "unknown.aparc.stats"
        dst.write_text(src.read_text())
        with pytest.raises(ValueError, match="hemisphere"):
            parse_aparc(dst)

    def test_empty_data_raises(self, tmp_path):
        bad = tmp_path / "lh.aparc.stats"
        bad.write_text("# ColHeaders StructName NumVert SurfArea\n")
        with pytest.raises(ValueError, match="data rows"):
            parse_aparc(bad)


# ---------------------------------------------------------------------------
# aseg.stats tests
# ---------------------------------------------------------------------------

class TestParseAseg:

    def test_returns_dataframe(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert isinstance(df, pd.DataFrame)

    def test_hemi_is_bilateral(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert (df["hemi"] == "bilateral").all()

    def test_atlas_is_aseg(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert (df["atlas"] == "aseg").all()

    def test_output_columns(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert list(df.columns) == ["hemi", "atlas", "region", "metric", "value", "units"]

    def test_index_not_in_metrics(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert "Index" not in df["metric"].unique()

    def test_segid_not_in_metrics(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert "SegId" not in df["metric"].unique()

    def test_metrics_are_numeric(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert pd.api.types.is_numeric_dtype(df["value"])

    def test_volume_units(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert (df.loc[df["metric"] == "Volume_mm3", "units"] == "mm3").all()

    def test_correct_row_count(self):
        # 3 structures x 7 metrics = 21 rows
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert len(df) == 21

    def test_structure_names_with_hyphens_preserved(self):
        df = parse_aseg(FIXTURES / "aseg.stats")
        assert "Left-Hippocampus" in df["region"].unique()
