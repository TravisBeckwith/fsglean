"""FreeSurfer stats file parsers."""

from fsglean.parsers.aparc import parse_aparc
from fsglean.parsers.aseg import parse_aseg
from fsglean.parsers.wmparc import parse_wmparc

__all__ = ["parse_aparc", "parse_aseg", "parse_wmparc"]
