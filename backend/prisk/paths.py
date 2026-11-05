"""Project-local paths used by runnable demo commands."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    """Return the repository root without depending on the note workspace."""
    return Path(__file__).resolve().parents[2]


def demo_data_root() -> Path:
    """Return the small, tracked demo dataset used by local startup commands."""
    return project_root() / "backend" / "data" / "demo"


def frozen_sample_data_root() -> Path:
    """Return the optional extracted v1.0 NetBox sample.

    This path is not a startup default. A later validation iteration can pass
    it through ``--stage03``, ``--stage04``, and ``--stage05``. The large
    stage04 file under this directory stays gitignored.
    """
    return project_root() / "backend" / "data" / "frozen-netbox"
