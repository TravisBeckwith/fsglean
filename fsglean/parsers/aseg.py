"""Parser for FreeSurfer aseg.stats files (subcortical segmentation)."""

from pathlib import Path

import pandas as pd

from fsglean.parsers._base import _parse_stats_file

ASEG_UNITS: dict[str, str] = {
    "NVoxels": "voxels",
    "Volume_mm3": "mm3",
    "normMean": "unitless",
    "normStd": "unitless",
    "normMin": "unitless",
    "normMax": "unitless",
    "normRange": "unitless",
}

# Columns that identify the structure but are not analysis metrics
_ASEG_ID_COLS: set[str] = {"Index", "SegId", "StructName"}


def parse_aseg(path: Path) -> pd.DataFrame:
    """Parse a FreeSurfer aseg.stats file into long format.

    Parameters
    ----------
    path : Path
        Path to the aseg.stats file.

    Returns
    -------
    pd.DataFrame
        Long-format table with columns:
        hemi, atlas, region, metric, value, units.

        hemi is set to 'bilateral' for all rows: aseg.stats is not split by
        hemisphere, though individual structure names encode laterality
        (e.g. Left-Hippocampus, Right-Hippocampus).

    Raises
    ------
    ValueError
        If the file is malformed.
    """
    path = Path(path)

    df = _parse_stats_file(path)

    metrics = [c for c in df.columns if c not in _ASEG_ID_COLS]
    long = df.melt(
        id_vars=["StructName"],
        value_vars=metrics,
        var_name="metric",
        value_name="value",
    ).rename(columns={"StructName": "region"})

    long["hemi"] = "bilateral"
    long["atlas"] = "aseg"
    long["units"] = long["metric"].map(ASEG_UNITS)

    return long[["hemi", "atlas", "region", "metric", "value", "units"]]
