"""FreeSurfer stats file parsers."""

from fsglean.parsers.aparc import parse_aparc
from fsglean.parsers.aseg import parse_aseg

__all__ = ["parse_aparc", "parse_aseg"]
