"""Parser for FreeSurfer wmparc.stats files (white matter parcellation)."""

from pathlib import Path

import pandas as pd

from fsglean.parsers._base import _parse_segmentation_stats

# wmparc.stats uses the same column structure and units as aseg.stats
# (Index SegId NVoxels Volume_mm3 StructName normMean normStd normMin
# normMax normRange) — see README "Note" under Supported input files.
WMPARC_UNITS: dict[str, str] = {
    "NVoxels": "voxels",
    "Volume_mm3": "mm3",
    "normMean": "unitless",
    "normStd": "unitless",
    "normMin": "unitless",
    "normMax": "unitless",
    "normRange": "unitless",
}


def parse_wmparc(path: Path) -> pd.DataFrame:
    """Parse a FreeSurfer wmparc.stats file into long format.

    Parameters
    ----------
    path : Path
        Path to the wmparc.stats file.

    Returns
    -------
    pd.DataFrame
        Long-format table with columns:
        hemi, atlas, region, metric, value, units.

        hemi is set to 'bilateral' for all rows: like aseg.stats, wmparc
        structures are not split across separate lh/rh files — laterality
        is encoded in the structure name instead (e.g. wm-lh-bankssts,
        wm-rh-bankssts).

    Raises
    ------
    ValueError
        If the file is malformed.
    """
    return _parse_segmentation_stats(path, atlas="wmparc", units=WMPARC_UNITS)
