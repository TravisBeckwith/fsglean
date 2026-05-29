"""Internal helpers shared across fsglean parsers."""

from pathlib import Path

import pandas as pd


def _parse_stats_file(filepath: Path) -> tuple:
    """
    Parse any FreeSurfer stats file that has a '# ColHeaders' line.

    Returns
    -------
    tuple of (col_headers: list[str], df: pd.DataFrame)
        col_headers is the ordered list of column names.
        df contains those columns; all non-StructName columns are cast
        to float via pd.to_numeric.

    Raises
    ------
    ValueError
        If no '# ColHeaders' line is found, or if the file has no data rows.
    """
    col_headers = None
    data_rows = []

    with open(filepath, "r") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            if line.startswith("# ColHeaders"):
                # "# ColHeaders StructName NumVert ..."
                # split() gives ['#', 'ColHeaders', 'StructName', ...]
                col_headers = line.split()[2:]
            elif line.startswith("#"):
                continue
            else:
                data_rows.append(line.split())

    if col_headers is None:
        raise ValueError(f"No '# ColHeaders' line found in {filepath}")

    if not data_rows:
        raise ValueError(f"No data rows found in {filepath}")

    df = pd.DataFrame(data_rows, columns=col_headers)

    numeric_cols = [c for c in col_headers if c != "StructName"]
    df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric, errors="coerce")

    return col_headers, df
