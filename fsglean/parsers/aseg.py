"""Parser for FreeSurfer aseg.stats files (subcortical segmentation)."""

from pathlib import Path

import pandas as pd

from fsglean.parsers._base import _parse_segmentation_stats

ASEG_UNITS: dict[str, str] = {
    "NVoxels": "voxels",
    "Volume_mm3": "mm3",
    "normMean": "unitless",
    "normStd": "unitless",
    "normMin": "unitless",
    "normMax": "unitless",
    "normRange": "unitless",
}


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
    return _parse_segmentation_stats(path, atlas="aseg", units=ASEG_UNITS)
