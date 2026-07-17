"""Registry of stat-type metadata: which files to look for, which parser
handles them, and human-readable metric descriptions for the data
dictionary.

This is the single place that knows about the mapping between a
user-facing ``--stats`` choice (e.g. ``"aparc.a2009s"``) and the actual
FreeSurfer filenames / parser / atlas label involved. Adding a new stats
type (e.g. a future ``aparc.a2009s`` variant or a new segmentation file)
should only require an entry here.
"""

from fsglean.parsers.aparc import APARC_UNITS, parse_aparc
from fsglean.parsers.aseg import ASEG_UNITS, parse_aseg
from fsglean.parsers.wmparc import WMPARC_UNITS, parse_wmparc

# ---------------------------------------------------------------------------
# Cortical (per-hemisphere) stats types
# ---------------------------------------------------------------------------
# Each entry maps a --stats choice to the filename stems for lh/rh and the
# parser used to read them.
CORTICAL_STATS: dict[str, dict] = {
    "aparc": {
        "lh_file": "lh.aparc.stats",
        "rh_file": "rh.aparc.stats",
        "parser": parse_aparc,
        "atlas": "desikan-killiany",
    },
    "aparc.a2009s": {
        "lh_file": "lh.aparc.a2009s.stats",
        "rh_file": "rh.aparc.a2009s.stats",
        "parser": parse_aparc,
        "atlas": "destrieux",
    },
    "aparc.DKTatlas": {
        "lh_file": "lh.aparc.DKTatlas.stats",
        "rh_file": "rh.aparc.DKTatlas.stats",
        "parser": parse_aparc,
        "atlas": "dkt",
    },
}

# ---------------------------------------------------------------------------
# Segmentation (bilateral, single-file) stats types
# ---------------------------------------------------------------------------
SEGMENTATION_STATS: dict[str, dict] = {
    "aseg": {
        "file": "aseg.stats",
        "parser": parse_aseg,
        "atlas": "aseg",
    },
    "wmparc": {
        "file": "wmparc.stats",
        "parser": parse_wmparc,
        "atlas": "wmparc",
    },
}

ALL_STATS_CHOICES = sorted(list(CORTICAL_STATS) + list(SEGMENTATION_STATS))

# ---------------------------------------------------------------------------
# Metric descriptions (from the FreeSurfer stats file metrics documented in
# the README). normRange isn't in FreeSurfer's own aseg/wmparc column header
# comments but appears in real output files, so it's included here too.
# ---------------------------------------------------------------------------
APARC_METRIC_DESCRIPTIONS: dict[str, str] = {
    "NumVert": "Number of vertices in the ROI",
    "SurfArea": "Surface area",
    "GrayVol": "Gray matter volume",
    "ThickAvg": "Mean cortical thickness",
    "ThickStd": "Standard deviation of cortical thickness",
    "MeanCurv": "Mean curvature",
    "GausCurv": "Gaussian curvature",
    "FoldInd": "Folding index",
    "CurvInd": "Intrinsic curvature index",
}

SEGMENTATION_METRIC_DESCRIPTIONS: dict[str, str] = {
    "NVoxels": "Number of voxels in the structure",
    "Volume_mm3": "Volume of the structure",
    "normMean": "Mean intensity of normalized volume",
    "normStd": "Standard deviation of intensity",
    "normMin": "Minimum intensity",
    "normMax": "Maximum intensity",
    "normRange": "Range of intensity (normMax - normMin)",
}

# All units and descriptions keyed by atlas, for lookup during dictionary
# generation.
UNITS_BY_ATLAS: dict[str, dict] = {
    "desikan-killiany": APARC_UNITS,
    "destrieux": APARC_UNITS,
    "dkt": APARC_UNITS,
    "aseg": ASEG_UNITS,
    "wmparc": WMPARC_UNITS,
}

METRIC_DESCRIPTIONS_BY_ATLAS: dict[str, dict] = {
    "desikan-killiany": APARC_METRIC_DESCRIPTIONS,
    "destrieux": APARC_METRIC_DESCRIPTIONS,
    "dkt": APARC_METRIC_DESCRIPTIONS,
    "aseg": SEGMENTATION_METRIC_DESCRIPTIONS,
    "wmparc": SEGMENTATION_METRIC_DESCRIPTIONS,
}

# atlas + hemi -> source filename, for the data dictionary's source_file column.
_CORTICAL_SOURCE_FILES = {
    ("desikan-killiany", "lh"): "lh.aparc.stats",
    ("desikan-killiany", "rh"): "rh.aparc.stats",
    ("destrieux", "lh"): "lh.aparc.a2009s.stats",
    ("destrieux", "rh"): "rh.aparc.a2009s.stats",
    ("dkt", "lh"): "lh.aparc.DKTatlas.stats",
    ("dkt", "rh"): "rh.aparc.DKTatlas.stats",
}
_SEGMENTATION_SOURCE_FILES = {
    "aseg": "aseg.stats",
    "wmparc": "wmparc.stats",
}


def source_file_for(atlas: str, hemi: str) -> str:
    """Return the FreeSurfer filename a given (atlas, hemi) row came from."""
    if atlas in _SEGMENTATION_SOURCE_FILES:
        return _SEGMENTATION_SOURCE_FILES[atlas]
    return _CORTICAL_SOURCE_FILES.get((atlas, hemi), f"{atlas}.stats")
