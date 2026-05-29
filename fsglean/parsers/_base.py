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
