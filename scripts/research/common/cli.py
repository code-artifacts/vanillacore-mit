"""Small helpers for consistent command-line behavior."""

from __future__ import annotations

import sys
from collections.abc import Callable

from .tooling import ResearchError


def execute(action: Callable[[], object]) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure:
            reconfigure(errors="replace")
    try:
        result = action()
    except (OSError, ResearchError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    if result is not None:
        print(result)
    return 0
