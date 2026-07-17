"""Core orchestration: FSGlean ties directory discovery (fsglean.io) and
per-file parsing (fsglean.parsers) together into the tidy, longitudinal,
multi-subject tables the README describes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, Sequence

import pandas as pd

from fsglean.io import find_sessions
from fsglean.registry import (
    ALL_STATS_CHOICES,
    CORTICAL_STATS,
    METRIC_DESCRIPTIONS_BY_ATLAS,
    SEGMENTATION_STATS,
    UNITS_BY_ATLAS,
    source_file_for,
)

_CORTICAL_ATLASES = {info["atlas"] for info in CORTICAL_STATS.values()}
_SEGMENTATION_ATLASES = {info["atlas"] for info in SEGMENTATION_STATS.values()}


def _sanitize(name: str) -> str:
    """Make a FreeSurfer structure/metric name safe as an R/pandas column
    fragment: hyphens and dots become underscores.
    """
    return name.replace("-", "_").replace(".", "_")


class FSGlean:
    """Extract and tabulate FreeSurfer stats across a BIDS derivatives tree.

    Parameters
    ----------
    derivatives_dir : str or Path
        Path to the FreeSurfer BIDS derivatives directory.
    stats : sequence of str, optional
        Stats files to extract. Choices: "aparc", "aparc.a2009s",
        "aparc.DKTatlas", "aseg", "wmparc". Default: ("aparc", "aseg").
    metrics : sequence of str, optional
        Restrict output to these metric names (e.g. "ThickAvg", "GrayVol").
        If omitted, all metrics for the requested stats are included.
    subjects : sequence of str, optional
        Restrict to these subject IDs (e.g. "sub-01"). If omitted, all
        discovered subjects are included.
    sessions : sequence of str, optional
        Restrict to these session IDs (e.g. "ses-V1"). If omitted, all
        discovered sessions are included.
    qc_threshold : float, optional
        Flag sub-ses rows with a value more than this many standard
        deviations from the cohort mean for that variable (hemi + atlas +
        region + metric). Default 4.0. Set to 0 to disable QC flagging.
    session_fallback : str or None, optional
        ``ses_id`` to use for cross-sectional subjects with no session
        level. Default "ses-01". Pass None to leave it unset instead
        (corresponds to the CLI's --no-session-fallback).

    Raises
    ------
    ValueError
        If an unknown stats choice is given, or if derivatives_dir does
        not exist.
    """

    def __init__(
        self,
        derivatives_dir,
        stats: Sequence[str] = ("aparc", "aseg"),
        metrics: Optional[Sequence[str]] = None,
        subjects: Optional[Sequence[str]] = None,
        sessions: Optional[Sequence[str]] = None,
        qc_threshold: float = 4.0,
        session_fallback: Optional[str] = "ses-01",
    ):
        self.derivatives_dir = Path(derivatives_dir)
        if not self.derivatives_dir.is_dir():
            raise ValueError(
                f"derivatives_dir does not exist or is not a directory: "
                f"{self.derivatives_dir}"
            )

        unknown = sorted(set(stats) - set(ALL_STATS_CHOICES))
        if unknown:
            raise ValueError(
                f"Unknown --stats choice(s): {unknown}. "
                f"Valid choices: {ALL_STATS_CHOICES}"
            )

        self.stats = list(stats)
        self.metrics = set(metrics) if metrics else None
        self.subjects = set(subjects) if subjects else None
        self.sessions = set(sessions) if sessions else None
        self.qc_threshold = qc_threshold
        self.session_fallback = session_fallback

        self._long_cache: Optional[pd.DataFrame] = None
        self._manifest_cache: Optional[pd.DataFrame] = None

    # ------------------------------------------------------------------
    # Session discovery (filtered)
    # ------------------------------------------------------------------

    def _sessions(self):
        for s in find_sessions(self.derivatives_dir, fallback_ses_id=self.session_fallback):
            if self.subjects is not None and s.sub_id not in self.subjects:
                continue
            if self.sessions is not None and s.ses_id not in self.sessions:
                continue
            yield s

    # ------------------------------------------------------------------
    # Collection: walk sessions, parse requested stats files, build the
    # master long table and the manifest in a single pass.
    # ------------------------------------------------------------------

    def _collect(self):
        if self._long_cache is not None:
            return

        long_frames = []
        manifest_rows = []

        cortical_keys = [k for k in self.stats if k in CORTICAL_STATS]
        segmentation_keys = [k for k in self.stats if k in SEGMENTATION_STATS]

        any_sessions = False
        for session in self._sessions():
            any_sessions = True
            row = {"sub_id": session.sub_id, "ses_id": session.ses_id}
            missing = []

            for key in cortical_keys:
                info = CORTICAL_STATS[key]
                for hemi_attr, hemi in (("lh_file", "lh"), ("rh_file", "rh")):
                    filename = info[hemi_attr]
                    found_col = f"{hemi}_{_sanitize(key)}_found"
                    path = session.stats_file(filename)
                    if path is None:
                        row[found_col] = False
                        missing.append(filename)
                        continue
                    row[found_col] = True
                    df = info["parser"](path, hemi=hemi)
                    df.insert(0, "ses_id", session.ses_id)
                    df.insert(0, "sub_id", session.sub_id)
                    long_frames.append(df)

            for key in segmentation_keys:
                info = SEGMENTATION_STATS[key]
                filename = info["file"]
                found_col = f"{_sanitize(key)}_found"
                path = session.stats_file(filename)
                if path is None:
                    row[found_col] = False
                    missing.append(filename)
                    continue
                row[found_col] = True
                df = info["parser"](path)
                df.insert(0, "ses_id", session.ses_id)
                df.insert(0, "sub_id", session.sub_id)
                long_frames.append(df)

            row["notes"] = "; ".join(f"{m} missing" for m in missing)
            manifest_rows.append(row)

        if long_frames:
            long_df = pd.concat(long_frames, ignore_index=True)
        else:
            long_df = pd.DataFrame(
                columns=["sub_id", "ses_id", "hemi", "atlas", "region", "metric", "value", "units"]
            )

        if self.metrics is not None and not long_df.empty:
            long_df = long_df[long_df["metric"].isin(self.metrics)].reset_index(drop=True)

        manifest_df = pd.DataFrame(manifest_rows)
        if not any_sessions:
            manifest_df = pd.DataFrame(columns=["sub_id", "ses_id", "notes"])

        if self.qc_threshold and self.qc_threshold > 0 and not long_df.empty and not manifest_df.empty:
            manifest_df = self._apply_qc_flags(long_df, manifest_df)
        else:
            manifest_df["qc_flag"] = False
            manifest_df["qc_flag_metrics"] = ""

        self._long_cache = long_df
        self._manifest_cache = manifest_df

    def _apply_qc_flags(self, long_df: pd.DataFrame, manifest_df: pd.DataFrame) -> pd.DataFrame:
        group_cols = ["hemi", "atlas", "region", "metric"]
        stats = long_df.groupby(group_cols)["value"].agg(["mean", "std"]).reset_index()
        merged = long_df.merge(stats, on=group_cols, how="left")
        # A variable with zero variance across the cohort (or only observed
        # once) has no meaningful z-score — treat it as never flaggable
        # rather than dividing by zero.
        safe_std = merged["std"].replace(0, pd.NA)
        merged["z"] = (merged["value"] - merged["mean"]) / safe_std
        merged["flagged"] = (merged["z"].abs() > self.qc_threshold).fillna(False)
        merged["variable_label"] = merged.apply(
            lambda r: f"{r['hemi']}_{_sanitize(str(r['region']))}_{r['metric']}", axis=1
        )

        flags = (
            merged[merged["flagged"]]
            .groupby(["sub_id", "ses_id"])["variable_label"]
            .apply(lambda s: "; ".join(sorted(set(s))))
            .reset_index()
            .rename(columns={"variable_label": "qc_flag_metrics"})
        )

        manifest_df = manifest_df.merge(flags, on=["sub_id", "ses_id"], how="left")
        manifest_df["qc_flag_metrics"] = manifest_df["qc_flag_metrics"].fillna("")
        manifest_df["qc_flag"] = manifest_df["qc_flag_metrics"] != ""
        return manifest_df

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def to_long(self, kind: Optional[str] = None) -> pd.DataFrame:
        """Return the long-format table: one row per sub x ses x hemi x
        region x metric.

        Parameters
        ----------
        kind : {"cortical", "subcortical", None}, optional
            Restrict to cortical (aparc-family) or subcortical/WM
            (aseg/wmparc) rows. Default None returns everything requested.
        """
        self._collect()
        df = self._long_cache
        if kind == "cortical":
            return df[df["atlas"].isin(_CORTICAL_ATLASES)].reset_index(drop=True)
        if kind == "subcortical":
            return df[df["atlas"].isin(_SEGMENTATION_ATLASES)].reset_index(drop=True)
        if kind is not None:
            raise ValueError(f"kind must be 'cortical', 'subcortical', or None, got {kind!r}")
        return df.reset_index(drop=True)

    def to_wide(self) -> pd.DataFrame:
        """Return the wide-format table: one row per sub x ses, all
        region x metric combinations as columns.

        Cortical columns are named ``{hemi}_{region}_{metric}`` (e.g.
        ``lh_bankssts_ThickAvg``). Subcortical/WM columns are named
        ``{region}_{metric}`` with hyphens sanitized to underscores (e.g.
        ``Left_Hippocampus_Volume_mm3``).

        Raises
        ------
        ValueError
            If two requested atlases would produce the same wide column
            name (e.g. two cortical atlases sharing a region name) — pivot
            to wide format one cortical atlas at a time in that case.
        """
        long_df = self.to_long()
        if long_df.empty:
            return pd.DataFrame(columns=["sub_id", "ses_id"])

        df = long_df.copy()
        is_cortical = df["atlas"].isin(_CORTICAL_ATLASES)
        df["wide_col"] = ""
        df.loc[is_cortical, "wide_col"] = (
            df.loc[is_cortical, "hemi"]
            + "_"
            + df.loc[is_cortical, "region"].map(_sanitize)
            + "_"
            + df.loc[is_cortical, "metric"]
        )
        df.loc[~is_cortical, "wide_col"] = (
            df.loc[~is_cortical, "region"].map(_sanitize) + "_" + df.loc[~is_cortical, "metric"]
        )

        collisions = (
            df.groupby("wide_col")["atlas"].nunique().loc[lambda s: s > 1]
        )
        if len(collisions) > 0:
            raise ValueError(
                "Wide-format column name collision between atlases for: "
                f"{list(collisions.index)}. Request one cortical atlas at a "
                "time (via --stats) when producing wide-format output, or "
                "call to_wide() per-atlas and merge manually."
            )

        wide = df.pivot_table(
            index=["sub_id", "ses_id"], columns="wide_col", values="value", aggfunc="first"
        ).reset_index()
        wide.columns.name = None
        return wide

    def data_dictionary(self) -> pd.DataFrame:
        """Return a data dictionary: one row per wide-format column,
        documenting its description, units, atlas, source file, and the
        underlying FreeSurfer metric name.

        Region descriptions are generated generically from the FreeSurfer
        structure code (e.g. "bankssts") rather than hand-translated
        anatomical prose (e.g. "banks of the superior temporal sulcus") —
        fsglean does not ship a FreeSurfer region-name lookup table, so it
        does not fabricate anatomical descriptions it can't verify.
        """
        long_df = self.to_long()
        if long_df.empty:
            return pd.DataFrame(
                columns=["column_name", "description", "units", "atlas", "source_file", "freesurfer_metric"]
            )

        df = long_df.drop_duplicates(subset=["hemi", "atlas", "region", "metric"]).copy()
        is_cortical = df["atlas"].isin(_CORTICAL_ATLASES)

        rows = []
        for _, r in df.iterrows():
            metric_desc = METRIC_DESCRIPTIONS_BY_ATLAS.get(r["atlas"], {}).get(r["metric"], r["metric"])
            units = UNITS_BY_ATLAS.get(r["atlas"], {}).get(r["metric"], r["units"])
            source_file = source_file_for(r["atlas"], r["hemi"])

            if r["atlas"] in _CORTICAL_ATLASES:
                hemi_word = {"lh": "left", "rh": "right"}.get(r["hemi"], r["hemi"])
                column_name = f"{r['hemi']}_{_sanitize(str(r['region']))}_{r['metric']}"
                description = f"{metric_desc} for {hemi_word} hemisphere region '{r['region']}' ({r['atlas']} atlas)"
            else:
                column_name = f"{_sanitize(str(r['region']))}_{r['metric']}"
                description = f"{metric_desc} for structure '{r['region']}' ({r['atlas']})"

            rows.append(
                {
                    "column_name": column_name,
                    "description": description,
                    "units": units,
                    "atlas": r["atlas"],
                    "source_file": source_file,
                    "freesurfer_metric": r["metric"],
                }
            )

        out = pd.DataFrame(rows).drop_duplicates(subset=["column_name"]).reset_index(drop=True)
        return out.sort_values(["atlas", "column_name"]).reset_index(drop=True)

    def manifest(self) -> pd.DataFrame:
        """Return the subject-session manifest: which stats files were
        found for each sub x ses, plus QC flags (see qc_threshold).
        """
        self._collect()
        return self._manifest_cache.reset_index(drop=True)
