from __future__ import annotations

from pathlib import Path


def available(control_root: Path) -> bool:
    """Return whether a shared daemon control endpoint is present.

    The adapter remains opt-in and conservative: protocol details must be supplied
    by a supported host before live state can override event authority.
    """
    return control_root.exists() and any(control_root.iterdir())


def collect_live(*_args, **_kwargs):
    return None
