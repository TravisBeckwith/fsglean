"""fsglean: BIDS-aware extraction of FreeSurfer stats files into tidy, longitudinal tables."""

from fsglean.core import FSGlean
from fsglean.io import StatsSession, find_sessions
from fsglean.parsers import parse_aparc, parse_aseg, parse_wmparc

__version__ = "0.1.0"

__all__ = [
    "FSGlean",
    "StatsSession",
    "find_sessions",
    "parse_aparc",
    "parse_aseg",
    "parse_wmparc",
]
