"""
utils/stdio.py — Force UTF-8 output encoding on Windows.

Windows consoles default to cp1252 (charmap), which cannot encode the
Greek Delta (Δ, U+0394) that the LLM echoes back from ``Δ3d`` prompt
labels.  Printing such text through a cp1252 stream raises
``UnicodeEncodeError``, which propagated out of PortfolioAgent.run()
and crashed every EOD cycle — leaving zero PM decisions and therefore
zero backtest entries.

ensure_utf8_stdio() reconfigures sys.stdout/sys.stderr to UTF-8 with
errors='replace' so any Unicode in LLM output degrades to '?' instead
of killing the process.  Call it at every CLI/entry point.
"""

from __future__ import annotations

import sys
from typing import TextIO


def _force_utf8(stream: TextIO) -> None:
    """Reconfigure a text stream to UTF-8 with replace-error handling.

    ``errors='replace'`` guarantees a non-encodable character degrades to
    '?' instead of raising UnicodeEncodeError — the crash that killed every
    EOD cycle when the LLM echoed the Δ character from prompt labels.
    """
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError, OSError):
        # Non-reconfigurable streams (e.g. tests replacing sys.stdout with
        # a plain wrapper) — leave as-is; encoding is not the problem there.
        pass


def ensure_utf8_stdio() -> None:
    """Reconfigure sys.stdout and sys.stderr to UTF-8 (errors='replace')."""
    for stream in (sys.stdout, sys.stderr):
        if stream is not None:
            _force_utf8(stream)
