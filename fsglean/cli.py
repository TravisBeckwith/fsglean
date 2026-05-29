"""Command-line interface for fsglean (stub)."""

import click


@click.command()
@click.argument("derivatives_dir")
@click.option("--stats", multiple=True, default=["aparc", "aseg"])
@click.option("--output", default="./fsglean_output/")
def main(derivatives_dir, stats, output):
    """Extract FreeSurfer stats files from a BIDS derivatives directory."""
    click.echo(f"fsglean v0.1.0 — CLI coming in next release.")
    click.echo(f"derivatives_dir: {derivatives_dir}")
    click.echo(f"stats: {stats}")
    click.echo(f"output: {output}")
