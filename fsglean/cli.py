"""Command-line interface for fsglean."""

from pathlib import Path

import click

from fsglean.core import FSGlean
from fsglean.registry import ALL_STATS_CHOICES


@click.command()
@click.argument(
    "derivatives_dir",
    type=click.Path(exists=True, file_okay=False, dir_okay=True, path_type=Path),
)
@click.option(
    "--stats",
    multiple=True,
    type=click.Choice(ALL_STATS_CHOICES),
    default=("aparc", "aseg"),
    show_default=True,
    help="Stats files to extract. Repeat for multiple, e.g. --stats aparc --stats aseg.",
)
@click.option(
    "--metrics",
    multiple=True,
    help="Restrict to these metrics (e.g. --metrics ThickAvg --metrics GrayVol). "
    "Default: all metrics for the requested stats.",
)
@click.option(
    "--subjects",
    multiple=True,
    help="Restrict to these subject IDs (e.g. --subjects sub-01 --subjects sub-02). "
    "Default: all discovered subjects.",
)
@click.option(
    "--sessions",
    multiple=True,
    help="Restrict to these session IDs (e.g. --sessions ses-V1). "
    "Default: all discovered sessions.",
)
@click.option(
    "--output",
    default="./fsglean_output/",
    show_default=True,
    type=click.Path(file_okay=False, path_type=Path),
    help="Output directory. Created if it does not exist.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["long", "wide", "both"]),
    default="both",
    show_default=True,
    help="Output format.",
)
@click.option("--no-dict", is_flag=True, help="Skip data dictionary generation.")
@click.option("--no-manifest", is_flag=True, help="Skip manifest generation.")
@click.option(
    "--qc-threshold",
    type=float,
    default=4.0,
    show_default=True,
    help="Flag values more than N standard deviations from the cohort mean. Set to 0 to disable.",
)
@click.option(
    "--no-session-fallback",
    is_flag=True,
    help="Leave ses_id empty for cross-sectional subjects instead of defaulting to ses-01.",
)
def main(
    derivatives_dir,
    stats,
    metrics,
    subjects,
    sessions,
    output,
    output_format,
    no_dict,
    no_manifest,
    qc_threshold,
    no_session_fallback,
):
    """Extract FreeSurfer stats files from a BIDS derivatives directory into
    tidy tabular datasets.

    DERIVATIVES_DIR is the path to the FreeSurfer BIDS derivatives directory.
    """
    try:
        extractor = FSGlean(
            derivatives_dir=derivatives_dir,
            stats=list(stats),
            metrics=list(metrics) or None,
            subjects=list(subjects) or None,
            sessions=list(sessions) or None,
            qc_threshold=qc_threshold,
            session_fallback=None if no_session_fallback else "ses-01",
        )
    except ValueError as e:
        raise click.ClickException(str(e))

    manifest_df = extractor.manifest()
    if manifest_df.empty:
        click.echo(
            f"No subjects found under {derivatives_dir} "
            "(expected sub-*/[ses-*/]stats/ or sub-*_ses-*/stats/). Nothing to do."
        )
        return

    output.mkdir(parents=True, exist_ok=True)
    written = []

    if output_format in ("long", "both"):
        cortical = extractor.to_long(kind="cortical")
        if not cortical.empty:
            path = output / "cortical_long.csv"
            cortical.to_csv(path, index=False)
            written.append(path)

        subcortical = extractor.to_long(kind="subcortical")
        if not subcortical.empty:
            path = output / "subcortical_long.csv"
            subcortical.to_csv(path, index=False)
            written.append(path)

    if output_format in ("wide", "both"):
        try:
            wide = extractor.to_wide()
        except ValueError as e:
            raise click.ClickException(str(e))
        if not wide.empty:
            path = output / "merged_wide.csv"
            wide.to_csv(path, index=False)
            written.append(path)

    if not no_dict:
        dictionary = extractor.data_dictionary()
        if not dictionary.empty:
            path = output / "data_dictionary.csv"
            dictionary.to_csv(path, index=False)
            written.append(path)

    if not no_manifest:
        path = output / "manifest.csv"
        manifest_df.to_csv(path, index=False)
        written.append(path)

    n_subjects = manifest_df["sub_id"].nunique()
    n_sessions = len(manifest_df)
    click.echo(f"fsglean: {n_subjects} subject(s), {n_sessions} session(s) processed.")
    if "qc_flag" in manifest_df.columns and manifest_df["qc_flag"].any():
        n_flagged = int(manifest_df["qc_flag"].sum())
        click.echo(f"  {n_flagged} session(s) flagged by QC (see manifest.csv).")
    click.echo(f"Wrote {len(written)} file(s) to {output}:")
    for path in written:
        click.echo(f"  {path}")
