"""Helpers for writing report files to disk."""

from __future__ import annotations

from pathlib import Path


def prepare_report_output_path(output_path: str | Path) -> Path:
    """Ensure parent directory exists and remove an existing file at the path."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    return path


__all__ = ["prepare_report_output_path"]
