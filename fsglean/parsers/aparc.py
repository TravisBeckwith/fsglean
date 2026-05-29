"""Parser for FreeSurfer aparc.stats files (cortical parcellation)."""

from pathlib import Path
from typing import Optional

import pandas as pd

from fsglean.parsers._base import _parse_stats_file

APARC_UNITS: dict[str, str] = {
    "NumVert": "vertices",
    "SurfArea": "mm2",
    "GrayVol": "mm3",
    "ThickAvg": "mm",
    "ThickStd": "mm",
    "MeanCurv": "mm-1",
    "GausCurv": "mm-2",
    "FoldInd": "unitless",
    "CurvInd": "unitless",
}


def parse_aparc(path: Path, hemi: Optional[str] = None) -> pd.DataFrame:
    """Parse a FreeSurfer aparc.stats file into long format.

    Parameters
    ----------
    path : Path
        Path to the stats file. Accepted filenames: lh.aparc.stats,
        rh.aparc.stats, lh.aparc.a2009s.stats, rh.aparc.a2009s.stats,
        lh.aparc.DKTatlas.stats, rh.aparc.DKTatlas.stats.
    hemi : str, optional
        Hemisphere ('lh' or 'rh'). If None, inferred from the filename prefix.

    Returns
    -------
    pd.DataFrame
        Long-format table with columns:
        hemi, atlas, region, metric, value, units.

    Raises
    ------
    ValueError
        If hemisphere cannot be inferred from the filename and hemi is not
        provided, or if the file is malformed.
    """
    path = Path(path)

    if hemi is None:
        filename = path.name
        if filename.startswith("lh."):
            hemi = "lh"
        elif filename.startswith("rh."):
            hemi = "rh"
        else:
            raise ValueError(
                f"Cannot infer hemisphere from filename '{path.name}'. "
                "Expected a name starting with 'lh.' or 'rh.'. "
                "Pass hemi='lh' or hemi='rh' explicitly."
            )

    filename = path.name
    if "a2009s" in filename:
        atlas = "destrieux"
    elif "DKTatlas" in filename:
        atlas = "dkt"
    else:
        atlas = "desikan-killiany"

    df = _parse_stats_file(path)

    metrics = [c for c in df.columns if c != "StructName"]
    long = df.melt(
        id_vars=["StructName"],
        value_vars=metrics,
        var_name="metric",
        value_name="value",
    ).rename(columns={"StructName": "region"})

    long["hemi"] = hemi
    long["atlas"] = atlas
    long["units"] = long["metric"].map(APARC_UNITS)

    return long[["hemi", "atlas", "region", "metric", "value", "units"]]
