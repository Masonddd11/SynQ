"""
tests/test_stdio.py — Unit tests for utils/stdio.py.

Regression for the backtest zero-entries bug: PortfolioAgent.run() crashed
every EOD cycle with ``UnicodeEncodeError: 'charmap' codec can't encode
character '\\u0394'`` because Windows cp1252 stdout cannot encode the Δ
(Greek Delta) character that the LLM echoes back from the ``Δ3d`` prompt
labels.  ensure_utf8_stdio() reconfigures stdout/stderr so any Unicode
character in LLM output survives instead of killing the run.
"""

from __future__ import annotations

import io
import sys

import pytest

from utils.stdio import _force_utf8, ensure_utf8_stdio


def test_force_utf8_on_cp1252_wrapper_allows_delta():
    """S1: _force_utf8 reconfigures a cp1252 stream so Δ encodes without error."""
    wrapper = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")

    # RED state: cp1252 cannot encode Δ (U+0394)
    with pytest.raises(UnicodeEncodeError):
        wrapper.write("Δ3d rsi=+1.2")
        wrapper.flush()

    _force_utf8(wrapper)

    # GREEN state: writing the same string succeeds and produces UTF-8 bytes
    wrapper.write("Δ3d rsi=+1.2")
    wrapper.flush()
    raw = wrapper.buffer.getvalue()
    assert raw == "Δ3d rsi=+1.2".encode("utf-8")


def test_force_utf8_uses_replace_errors_for_unencodable():
    """S1: errors='replace' means even exotic chars degrade, never crash."""
    wrapper = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    _force_utf8(wrapper)

    # A private-use char is still not representable in UTF-8 via surrogatepass
    wrapper.write("ok \ud800 surrogate")
    wrapper.flush()
    raw = wrapper.buffer.getvalue()
    assert raw.startswith(b"ok ")


def test_ensure_utf8_stdio_keeps_process_running():
    """S1: ensure_utf8_stdio() applies to the real sys.stdout/sys.stderr."""
    old_out, old_err = sys.stdout, sys.stderr
    try:
        sys.stdout = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        sys.stderr = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
        ensure_utf8_stdio()
        # The crash that killed every EOD cycle must not raise
        print("Δ3d", flush=True)
        sys.stdout.flush()
        assert b"\xce\x94" in sys.stdout.buffer.getvalue()  # UTF-8 encoding of Δ
    finally:
        sys.stdout, sys.stderr = old_out, old_err
