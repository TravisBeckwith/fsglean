"""Shared low-level parser for FreeSurfer stats files."""

from pathlib import Path

import pandas as pd


def _parse_stats_file(path: Path) -> pd.DataFrame:
    """Parse a FreeSurfer stats file into a DataFrame.

    Reads the ``# ColHeaders`` comment line for column names and collects
    all non-comment, non-empty data rows. All columns except ``StructName``
    are cast to numeric.

    Parameters
    ----------
    path : Path
        Path to the stats file (e.g. lh.aparc.stats, aseg.stats).

    Returns
    -------
    pd.DataFrame
        One row per brain structure, one column per header field.

    Raises
    ------
    ValueError
        If no ``# ColHeaders`` line is found, or if the file contains no
        data rows.
    """
    columns = None
    rows = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("# ColHeaders"):
                columns = line.split()[2:]
            elif line.startswith("#") or not line:
                continue
            else:
                rows.append(line.split())

    if columns is None:
        raise ValueError(
            f"No '# ColHeaders' line found in {path}. "
            "Is this a valid FreeSurfer stats file?"
        )
    if not rows:
        raise ValueError(
            f"No data rows found in {path}. "
            "Is this a valid FreeSurfer stats file?"
        )

    df = pd.DataFrame(rows, columns=columns)

    for col in df.columns:
        if col != "StructName":
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df


# Columns that identify a segmentation structure but are not analysis
# metrics — shared by aseg.stats and wmparc.stats.
_SEGMENTATION_ID_COLS: set[str] = {"Index", "SegId", "StructName"}


def _parse_segmentation_stats(
    path: Path,
    atlas: str,
    units: dict,
    hemi: str = "bilateral",
) -> pd.DataFrame:
    """Shared parser for FreeSurfer segmentation-style stats files.

    Covers both ``aseg.stats`` and ``wmparc.stats``, which share the same
    column structure (``Index SegId NVoxels Volume_mm3 StructName normMean
    normStd normMin normMax normRange``) and differ only in which
    structures they enumerate and how ``units`` maps metric -> unit string.

    Parameters
    ----------
    path : Path
        Path to the stats file.
    atlas : str
        Value to record in the output ``atlas`` column (e.g. ``"aseg"``,
        ``"wmparc"``).
    units : dict
        Mapping of metric name -> unit string, used to populate the
        ``units`` column.
    hemi : str
        Value to record in the output ``hemi`` column. Both aseg and
        wmparc structures are not split into separate lh/rh files —
        laterality is encoded in the structure name instead (e.g.
        ``Left-Hippocampus``, ``wm-lh-bankssts``) — so this defaults to
        ``"bilateral"``.

    Returns
    -------
    pd.DataFrame
        Long-format table with columns: hemi, atlas, region, metric,
        value, units.
    """
    path = Path(path)
    df = _parse_stats_file(path)

    metrics = [c for c in df.columns if c not in _SEGMENTATION_ID_COLS]
    long = df.melt(
        id_vars=["StructName"],
        value_vars=metrics,
        var_name="metric",
        value_name="value",
    ).rename(columns={"StructName": "region"})

    long["hemi"] = hemi
    long["atlas"] = atlas
    long["units"] = long["metric"].map(units)

    return long[["hemi", "atlas", "region", "metric", "value", "units"]]
