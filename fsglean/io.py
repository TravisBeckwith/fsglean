"""BIDS-aware directory traversal for FreeSurfer derivatives."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class StatsSession:
    """A subject-session pair with a resolved stats directory."""

    sub_id: str
    ses_id: str
    stats_dir: Path

    def stats_file(self, name: str) -> Optional[Path]:
        """Return the path to a named stats file, or None if absent."""
        p = self.stats_dir / name
        return p if p.exists() else None


def find_sessions(
    derivatives_dir: Path,
    fallback_ses_id: str = "ses-01",
) -> Iterator[StatsSession]:
    """Walk a FreeSurfer BIDS derivatives directory and yield StatsSession objects.

    Supports three directory layouts:
    - Nested:          sub-01/ses-V1/stats/
    - Flat:            sub-01_ses-V1/stats/
    - Cross-sectional: sub-01/stats/
    """
    derivatives_dir = Path(derivatives_dir)

    for sub_dir in sorted(derivatives_dir.glob("sub-*")):
        if not sub_dir.is_dir():
            continue

        dir_name = sub_dir.name

        # Flat layout: sub-01_ses-V1/
        if "_ses-" in dir_name:
            actual_sub_id, ses_suffix = dir_name.split("_ses-", 1)
            ses_id = "ses-" + ses_suffix
            stats_dir = sub_dir / "stats"
            if stats_dir.is_dir():
                yield StatsSession(
                    sub_id=actual_sub_id,
                    ses_id=ses_id,
                    stats_dir=stats_dir,
                )
            continue

        # Nested layout: sub-01/ses-V1/stats/
        ses_dirs = sorted(sub_dir.glob("ses-*"))
        if ses_dirs:
            for ses_dir in ses_dirs:
                if not ses_dir.is_dir():
                    continue
                stats_dir = ses_dir / "stats"
                if stats_dir.is_dir():
                    yield StatsSession(
                        sub_id=dir_name,
                        ses_id=ses_dir.name,
                        stats_dir=stats_dir,
                    )
        else:
            # Cross-sectional: sub-01/stats/
            stats_dir = sub_dir / "stats"
            if stats_dir.is_dir():
                yield StatsSession(
                    sub_id=dir_name,
                    ses_id=fallback_ses_id,
                    stats_dir=stats_dir,
                )
